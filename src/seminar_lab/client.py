"""Responses APIの明示送信。再試行・自動フォールバック・自動収集なし。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from importlib.metadata import version
from math import isfinite
from threading import Lock
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

from .config import COURSE_MODELS, ValidationError, validate_runtime
from .inputs import PreparedInput
from .records import new_record

ERRORS = {
    "timeout": "応答待ちが時間切れになりました。課金状態は不明です。履歴を保存し、再送前に教員へ確認してください。",
    "authentication": "認証できません。キーを画面やログに貼らず、配布元へ確認してください。",
    "budget": "予算・利用枠の制限です。教員へ確認してください。自動再送はしません。",
    "rate_limit": "混雑・レート制限です。記録を保存し、教員の案内に従ってください。",
    "invalid_input": "入力または設定を受け付けられませんでした。範囲・形式・対応機能を確認してください。",
    "service_unavailable": "経路または予算基盤が利用できません。送信を止めて教員へ連絡してください。",
    "network": "通信できませんでした。処理・課金状態は不明です。接続を確認してください。",
    "interrupted": "送信を中断しました。サーバ側の処理・課金状態は不明です。この記録を保存し、再送前に教員へ確認してください。",
    "unknown": "問い合わせに失敗しました。詳細を公開せず教員へ確認してください。",
    "incomplete": "回答が完了していません。部分出力を記録しました。成功した履歴には追加していません。",
    "invalid_response": "想定した文章の応答形式ではありません。生応答を保存し、成功した履歴には追加していません。",
    "refusal": "モデルが回答を拒否しました。成功した対話として扱わず、入力を確認してください。",
    "model_mismatch": "応答のモデルが指定したモデルと一致しません。経路の設定を確認してください。",
    "model_access": "選択したモデルをこのAPIキーで利用できません。モデル名と、このキーが属するプロジェクトのモデル許可を教員へ確認してください。別モデルへは自動で切り替えません。",
}


class TransportError(Exception):
    """秘密を含まない分類済みの通信障害。"""
    def __init__(self, kind: str):
        self.kind = kind if kind in ERRORS else "unknown"
        super().__init__(ERRORS[self.kind])


class Transport(Protocol):
    """外部呼出し境界。人工応答はtests内だけで実装する。"""
    def send(self, payload: dict) -> dict: ...


@dataclass
class LivePermission:
    """教員等が明示的に許可した対象・枠。APIキーの存在を許可とみなさない。"""
    approved_by: str
    scope: str
    route: str
    model: str
    authentication_route: str
    usd_limit: float
    request_limit: int
    used: int = 0
    _lock: Any = field(default_factory=Lock, repr=False, compare=False)

    def validate(self, runtime: dict) -> None:
        """通信・回数の消費なしで許可対象と残り枠を確認する。"""
        if not all(isinstance(v, str) and v.strip() for v in (self.approved_by, self.scope, self.authentication_route)) or self.route != runtime["route"] or self.model != runtime["model"]:
            raise ValidationError("明示的な許可の対象・認証経路が一致しません。")
        if (type(self.usd_limit) not in (int, float) or not isfinite(self.usd_limit) or self.usd_limit <= 0
                or type(self.request_limit) is not int or self.request_limit < 1
                or type(self.used) is not int or not 0 <= self.used < self.request_limit):
            raise ValidationError("許可された呼出し枠がありません。")

    def consume(self, runtime: dict) -> None:
        """送信回数を先に予約する。失敗時も戻さない。金額制限はサーバ側で別途確認。"""
        with self._lock:
            self.validate(runtime)
            self.used += 1


class OpenAITransport:
    """キーはメモリ内だけに置き、SDKの再試行を0回にする。"""
    def __init__(self, runtime: dict, api_key: str, permission: "LivePermission | None" = None):
        try:
            rule = runtime["capabilities"]["parameters"]["max_output_tokens"]
            # 接続設定の検査用。実送信値はSession.previewで毎回別に検査する。
            validation_limit = rule["min"] if "min" in rule else rule["values"][0]
        except (KeyError, TypeError, IndexError):
            raise ValidationError("出力上限の対応表をmin/maxまたは空でないvaluesで設定してください。") from None
        validate_runtime(runtime, {"text"}, {"max_output_tokens": validation_limit})
        if not api_key or version("openai") != runtime["sdk_version"]:
            raise ValidationError("キーまたはSDKの固定版を確認してください。")
        from openai import OpenAI
        import httpx
        self._runtime = deepcopy(runtime)
        self._permission = permission
        self._lock = Lock()
        self._client = OpenAI(api_key=api_key, base_url=runtime["base_url"], max_retries=0,
                              timeout=runtime["timeout_seconds"], http_client=httpx.Client(follow_redirects=False, trust_env=False))

    def close(self) -> None:
        """この送信経路のHTTP接続を閉じる。"""
        self._client.close()

    def send(self, payload: dict) -> dict:
        """1回だけ送る。教員用試験で許可枠を指定した場合だけ回数を管理する。"""
        from openai import APIConnectionError, APIStatusError, APITimeoutError
        if payload.get("model") != self._runtime["model"]:
            raise ValidationError("送信モデルが許可の対象と異なります。")
        if self._permission is not None:
            with self._lock:
                self._permission.consume(self._runtime)
        try:
            return self._client.responses.create(**payload).model_dump(mode="json")
        except APITimeoutError:
            raise TransportError("timeout") from None
        except APIConnectionError:
            raise TransportError("network") from None
        except APIStatusError as exc:
            code = getattr(exc, "code", None)
            kind = {401: "authentication", 403: "authentication", 400: "invalid_input", 413: "invalid_input", 422: "invalid_input", 429: "rate_limit", 503: "service_unavailable"}.get(exc.status_code, "unknown")
            if code in {"insufficient_quota", "budget_exceeded", "budget_exceeded_error"}:
                kind = "budget"
            elif code in {"model_not_found", "model_not_available", "model_access_denied"}:
                kind = "model_access"
            raise TransportError(kind) from None
        except Exception:
            raise TransportError("unknown") from None


@dataclass
class Session:
    """1人分の状態。継続時に過去の入出力を全て送る。切捨てなし。"""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    _history: list[dict] = field(default_factory=list, repr=False)
    _runs: set[str] = field(default_factory=set, repr=False)
    _context: tuple | None = field(default=None, repr=False)
    _runtime: dict | None = field(default=None, repr=False)
    _turn_count: int = 0
    _lock: Any = field(default_factory=Lock, repr=False)
    records: list[dict] = field(default_factory=list)

    @property
    def history(self) -> list[dict]:
        """外部から内部の履歴を書換えないようコピーを返す。"""
        return deepcopy(self._history)

    def check_run_id(self, run_id: str) -> None:
        """キー入力前にも、実行済み番号や空の番号を拒否できるようにする。"""
        if not isinstance(run_id, str) or not run_id.strip() or run_id in self._runs:
            raise ValidationError("この実行番号は空か実行済みです。保存後に『次の実行番号』を実行してください。")

    def preview(self, runtime: dict, prompt: str, inputs: list[PreparedInput], mode: str, parameters: dict) -> dict:
        """送信する全履歴を構築する。通信しない。"""
        if mode not in {"new", "continue"} or not isinstance(prompt, str) or not prompt.strip():
            raise ValidationError("質問と新規/継続を明示してください。")
        for item in inputs:
            item.validate()
        validate_runtime(runtime, {"text"} | {i.kind for i in inputs}, parameters)
        if mode == "continue" and not self._history:
            raise ValidationError("継続する成功済み履歴がありません。新規を選んでください。")
        if mode == "continue" and any((self._runtime or {}).get(k) != runtime.get(k)
                                      for k in ("route", "api", "model", "base_url")):
            raise ValidationError("継続途中のモデル・経路変更は新規会話で行ってください。")
        content = [deepcopy(i.content) for i in inputs] + [{"type": "input_text", "text": prompt}]
        payload = {"model": runtime["model"], "input": (self.history if mode == "continue" else []) + [{"role": "user", "content": content}],
                   "store": False, "truncation": "disabled", **deepcopy(parameters)}
        if runtime["model"] in {"gpt-6-luna", "gpt-6.1-sol"}:
            # store=Falseでも継続できる暗号化データ。内部の思考本文は取得・表示しない。
            payload["include"] = ["reasoning.encrypted_content"]
        return payload

    def run(self, *, runtime: dict, context: dict, prompt: str, inputs: list[PreparedInput],
            mode: str, parameters: dict, run_id: str, transport: Transport) -> dict:
        """成功時だけ会話を確定。重複runは失敗後を含め再送しない。"""
        if not self._lock.acquire(blocking=False):
            raise ValidationError("この会話で送信中です。終了を待ってください。")
        try:
            self.check_run_id(run_id)
            if context.get("phase") == "R0":
                raise ValidationError("R0ではAIを呼び出せません。")
            if context.get("selection_origin") == "student":
                review = context.get("input_review", {})
                if review.get("status") != "confirmed" or not review.get("reviewer"):
                    raise ValidationError("学生選定資料の入力確認が必要です。")
            elif context.get("adoption") != "adopted" or context.get("rights", {}).get("ai_input") != "confirmed":
                raise ValidationError("素材の採用・AI入力確認待ちです。")
            identity = tuple(str(context.get(k)) for k in ("material_id", "source_version", "assigned_scope"))
            if mode == "continue" and identity != self._context:
                raise ValidationError("異なる素材・版・指定範囲は新規会話にしてください。")
            payload = self.preview(runtime, prompt, inputs, mode, parameters)
            record = new_record(context, self.session_id)
            record.update(run_id=run_id, conversation_mode=mode, prior_turn_count=self._turn_count if mode == "continue" else 0,
                          prompt=prompt, input_kind=[i.kind for i in inputs] or ["text"],
                          input_scope=[deepcopy(i.provenance.get("input_scope")) for i in inputs],
                          input_provenance=[deepcopy(i.provenance) for i in inputs],
                          file_hash=[i.provenance.get("file_hash") for i in inputs],
                          service="OpenAI API", access_route=runtime["route"], requested_model=runtime["model"],
                          parameters_requested=deepcopy(parameters), tool_usage=[], status="pending")
            # 実際に送った抜粋・添付・履歴を学生側の明示保存に残す。
            record["request_input"] = deepcopy(payload["input"])
            self._runs.add(run_id)
            start = monotonic()
            try:
                raw = transport.send(payload)
                if not isinstance(raw, dict):
                    raise TransportError("invalid_response")
                safe_raw = deepcopy(raw)
                # 正常な出力本文は維持。上流エラーの自由文には認証情報が入り得る。
                if safe_raw.get("error"):
                    safe_raw["error"] = {"type": "upstream_error", "message": ERRORS["unknown"]}
                record.update(response_raw=safe_raw, reported_model=raw.get("model"), usage=raw.get("usage"))
                if raw.get("status") == "failed" or raw.get("error"):
                    record.update(status="failed", error_type="unknown", error_message=ERRORS["unknown"])
                elif raw.get("status") == "incomplete":
                    record.update(status="incomplete", error_type="incomplete", error_message=ERRORS["incomplete"])
                elif raw.get("status") != "completed":
                    raise TransportError("invalid_response")
                else:
                    validate_response(raw, runtime["model"])
                    record["status"] = "success"
                    record["parameters_confirmed"] = {k: raw[k] for k in parameters if k in raw}
                    self._history = deepcopy(payload["input"]) + deepcopy(raw["output"])
                    self._turn_count = (self._turn_count if mode == "continue" else 0) + 1
                    self._context, self._runtime = identity, deepcopy(runtime)
            except KeyboardInterrupt:
                # 停止ボタンでも、送信した可能性のある問い合わせを記録から落とさない。
                record.update(status="failed", error_type="interrupted", error_message=ERRORS["interrupted"])
            except Exception as exc:
                kind = exc.kind if isinstance(exc, TransportError) else "unknown"
                record.update(status="failed", error_type=kind, error_message=ERRORS[kind])
            record["elapsed_seconds"] = monotonic() - start
            self.records.append(deepcopy(record))
            return record
        finally:
            self._lock.release()


def output_text(record: dict) -> str:
    """生応答は保存したまま、画面用テキストだけを取り出す。"""
    raw = record.get("response_raw")
    if raw is None:
        return ""
    if not isinstance(raw, dict):
        raise ValidationError("生応答が辞書形式ではありません。元の記録を確認してください。")
    output = raw.get("output", [])
    if not isinstance(output, list):
        raise ValidationError("応答のoutputが配列ではありません。生応答とエラー分類を確認してください。")
    texts = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            raise ValidationError("応答本文の構造が不正です。生応答とエラー分類を確認してください。")
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                if not isinstance(part.get("text"), str):
                    raise ValidationError("応答本文が文字列ではありません。元の記録を確認してください。")
                texts.append(part["text"])
    return "\n".join(texts)


def validate_response(raw: dict, requested_model: str) -> None:
    """文章だけを求めた経路の成功条件。拒否・ツール呼出し・別モデルは成功にしない。"""
    accepted = COURSE_MODELS.get(requested_model, {}).get("reported_models", [requested_model])
    if raw.get("model") not in accepted:
        raise TransportError("model_mismatch")
    output = raw.get("output")
    if not isinstance(output, list) or not output:
        raise TransportError("invalid_response")
    has_text = False
    for item in output:
        if not isinstance(item, dict):
            raise TransportError("invalid_response")
        if item.get("type") == "reasoning":
            # 公開された応答メタデータだけを保持し、内部思考の取得は要求しない。
            continue
        if item.get("type") != "message" or item.get("role") != "assistant" or item.get("status") != "completed":
            raise TransportError("invalid_response")
        content = item.get("content")
        if not isinstance(content, list) or not content:
            raise TransportError("invalid_response")
        for part in content:
            if not isinstance(part, dict):
                raise TransportError("invalid_response")
            if part.get("type") == "refusal":
                raise TransportError("refusal")
            if part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                raise TransportError("invalid_response")
            has_text |= bool(part["text"].strip())
    if not has_text:
        raise TransportError("invalid_response")

"""教員が用意した接続設定を読む。キーの読込み・送信・許可の自動発行はしない。"""
from __future__ import annotations

from dataclasses import fields
from copy import deepcopy
from pathlib import Path

from .client import LivePermission
from .config import COURSE_MODELS, ValidationError, load_yaml, validate_runtime


def load_runtime(path: str | Path, model: str | None = None) -> dict:
    """授業用接続を読む。利用額・回数の上限は教員がAPI側で管理する。

    旧ファイルのpermissionと出力トークンの範囲は授業では使用しない。
    回答長は質問セルで指定し、モデルの対応上限はAPIが判定する。
    """
    config = load_yaml(path)
    if not isinstance(config, dict) or "runtime" not in config or set(config) - {"runtime", "permission"}:
        raise ValidationError("接続ファイルにruntimeを記入してください。APIキーは含めません。")
    runtime = config["runtime"]
    if not isinstance(runtime, dict):
        raise ValidationError("runtimeは接続設定の辞書にしてください。")
    capabilities = runtime.get("capabilities")
    if not isinstance(capabilities, dict) or not isinstance(capabilities.get("parameters"), dict):
        raise ValidationError("接続設定に対応機能とparametersを記入してください。")
    # 旧版の512固定も解除。APIの技術的な上限・対応外設定はAPIエラーとして表示する。
    capabilities["parameters"]["max_output_tokens"] = {"min": 1}
    validate_runtime(runtime, {"text"}, {"max_output_tokens": 2048})
    return select_model(runtime, model) if model is not None else runtime


def select_model(runtime: dict, model: str) -> dict:
    """採用済みのモデルを明示選択する。直接APIの仕様を中継へ流用しない。"""
    if model not in COURSE_MODELS:
        raise ValidationError("モデルはgpt-6-luna / gpt-6-sol / gpt-4.1-miniから選んでください。")
    selected = deepcopy(runtime)
    if selected["route"] != "direct_openai":
        if selected["model"] != model:
            raise ValidationError("中継接続のモデル変更には、そのモデルで確認した接続ファイルが必要です。")
        return selected
    profile = COURSE_MODELS[model]
    parameters = {"max_output_tokens": {"min": 1}}
    if profile["sampling"]:
        parameters.update(temperature={"min": 0, "max": 2}, top_p={"min": 0, "max": 1})
    if profile["reasoning_efforts"]:
        parameters["reasoning"] = {"values": [{"effort": value} for value in profile["reasoning_efforts"]]}
    selected["model"] = model
    selected["capabilities"]["parameters"] = parameters
    # 接続先の確認記録は保持。モデルごとの実測状態をpassへ書換えない。
    validate_runtime(selected, {"text"}, {"max_output_tokens": 2048})
    return selected


def load_connection(path: str | Path, permissions: dict[str, LivePermission]) -> tuple[dict, LivePermission]:
    """教員用試験の明示した回数枠を読む。授業Notebookはload_runtimeを使う。"""
    config = load_yaml(path)
    if set(config) != {"runtime", "permission"}:
        raise ValidationError("接続ファイルにはruntimeとpermissionだけを記入してください。キーは含めません。")
    runtime, grant = config["runtime"], config["permission"]
    names = {item.name for item in fields(LivePermission)} - {"used", "_lock"}
    if not isinstance(grant, dict) or set(grant) != names | {"id"}:
        raise ValidationError("教員の送信許可に不足・未対応の項目があります。配布元へ確認してください。")
    grant_id = grant["id"]
    if not isinstance(grant_id, str) or not grant_id.strip():
        raise ValidationError("送信許可の識別名が必要です。配布元へ確認してください。")
    # Notebookの最初の出力上限。対応外の経路はキー入力の前に止める。
    validate_runtime(runtime, {"text"}, {"max_output_tokens": 512})
    proposed = LivePermission(**{name: grant[name] for name in names})
    proposed.validate(runtime)
    if grant_id in permissions:
        previous = permissions[grant_id]
        if not isinstance(previous, LivePermission) or any(getattr(previous, name) != grant[name] for name in names):
            raise ValidationError("同じ識別名で送信許可が変更されています。使用回数をリセットせず、配布元へ確認してください。")
        previous.validate(runtime)
        return runtime, previous
    permissions[grant_id] = proposed
    return runtime, proposed

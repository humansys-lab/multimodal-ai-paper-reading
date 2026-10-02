"""API/GUI/AIなしの共通記録。JSONLとMarkdownを情報を落とさず往復する。"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import json
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import ACTIVITY_NAMES, PHASES, ValidationError

FIELDS = """session_id run_id activity_id phase timestamp material_id material_role selection_origin
source_version file_hash assigned_scope input_scope page_or_figure service access_route requested_model
reported_model conversation_mode prior_turn_count tool_usage input_kind prompt visible_system_instructions
parameters_requested parameters_confirmed response_raw status error_type retry_count usage cost_value cost_kind
elapsed_seconds student_explanation evidence_location verification_status peer_insight unresolved_point next_change
student_revision change_reason question_set_id input_review input_provenance error_message request_input""".split()


def new_record(context: dict, session_id: str | None = None) -> dict[str, Any]:
    """空の個人記録を作る。費用不明や該当なしはnullを維持する。"""
    r = dict.fromkeys(FIELDS)
    r.update(session_id=session_id or str(uuid4()), run_id=str(uuid4()), timestamp=datetime.now(timezone.utc).isoformat(),
             status="draft", cost_kind="unknown", retry_count=0, visible_system_instructions=[])
    for key in ("activity_id", "phase", "material_id", "selection_origin", "source_version", "assigned_scope", "question_set_id", "input_review"):
        r[key] = deepcopy(context.get(key))
    r["material_role"] = context.get("role")
    # 追加項目として保存し、旧記録の読込み互換性を保つ。
    r['source_material_id'] = context.get('source_material_id', context.get('material_id'))
    r['source_file_hash'] = context.get('file_hash')
    for key in ('eligibility_review', 'bibliography', 'doi', 'source_url', 'file_hash',
                'publication_status', 'article_type', 'open_access', 'license'):
        r[key] = deepcopy(context.get(key))
    return r


def validate_record(record: dict) -> None:
    """P01の段階とHomeworkの混在、費用の誤表示を防ぐ。"""
    if not isinstance(record, dict) or any(k not in record for k in FIELDS):
        raise ValidationError("記録の必須フィールドが不足しています。")
    aid, phase = record["activity_id"], record["phase"]
    if aid in PHASES and phase != PHASES[aid]:
        raise ValidationError("共通課題とR0～R3の対応が不正です。")
    if phase in {"R0", "R1", "R2", "R3"} and (record["material_id"] != "P01" or PHASES.get(aid) != phase):
        raise ValidationError("R0～R3は対応するP01共通課題専用です。")
    if aid == "HW1" and phase != "homework":
        raise ValidationError("HW1はhomework記録として保存してください。")
    fixed = {'METHODS': ('M01', None, 'Q_METHODS_5'), 'TRANSFER': ('P02', 'transfer', 'Q_TRANSFER_3')}
    if aid in fixed and (record['material_id'], phase, record['question_set_id']) != fixed[aid]:
        raise ValidationError('Methodsと別論文への応用は、それぞれ固定した素材・段階・設問で保存してください。')
    if phase == "R0" and (record["response_raw"] is not None or record["service"] not in {None, "none"}):
        raise ValidationError("R0はAIなしの記録です。")
    if record["cost_kind"] == "unknown" and record["cost_value"] is not None:
        raise ValidationError("費用不明を数値で埋めないでください。")
    if not all(isinstance(record[k], str) and record[k].strip() for k in ("session_id", "run_id")):
        raise ValidationError("記録IDが必要です。")
    for key in ("cost_value", "elapsed_seconds"):
        value = record[key]
        if value is not None and (type(value) not in (int, float) or not isfinite(value) or value < 0):
            raise ValidationError("費用・所要時間は非負の有限数またはnullにしてください。")


def _unique_records(records: list[dict]) -> None:
    """保存と再読込みの両方で、記録の配列とrunの一意性を確認する。"""
    if not isinstance(records, list):
        raise ValidationError("記録は配列として保存してください。")
    for record in records:
        validate_record(record)
    ids = [(r["session_id"], r["run_id"]) for r in records]
    if len(ids) != len(set(ids)):
        raise ValidationError("同じrunが重複しています。")


def _json_object(pairs: list[tuple]) -> dict:
    """同名フィールドが二つあるJSONを、後勝ちで読まない。"""
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError("JSONのフィールド名が重複しています。元の記録を確認してください。")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    """NaNやInfinityはJSONの数値として受け付けない。"""
    raise ValidationError("JSONに非標準の数値が含まれています。")


def _finite_json_float(value: str) -> float:
    """桁あふれをInfinityへ変換せず拒否する。"""
    number = float(value)
    if not isfinite(number):
        raise ValidationError("JSONの数値が大きすぎます。")
    return number


def _read_json(content: str) -> Any:
    """壊れたJSONを補修・欠落扱いせず、明示的に拒否する。"""
    try:
        return json.loads(content, object_pairs_hook=_json_object, parse_constant=_reject_json_constant,
                          parse_float=_finite_json_float)
    except json.JSONDecodeError:
        raise ValidationError("JSONを読み込めません。元の記録ファイルを確認してください。") from None


def record_json(value: Any, *, indent: int | None = None) -> str:
    """保存で型や項目が変わる値を、ファイル作成前に拒否する。"""
    try:
        content = json.dumps(value, ensure_ascii=False, indent=indent, allow_nan=False)
    except (TypeError, ValueError):
        raise ValidationError("記録にJSONで保存できない値があります。文字列・数値・null・リスト・辞書を使ってください。") from None
    if _read_json(content) != value:
        raise ValidationError("保存すると記録の型が変わります。辞書のキーは文字列、配列はリストにしてください。")
    return content


def _readable_response(raw: Any) -> str:
    """壊れた応答も保存できるよう、表示可能な文章だけを一覧へ取り出す。"""
    if isinstance(raw, str):
        return raw
    if raw is None:
        return 'AIの応答なし'
    texts = []
    if isinstance(raw, dict) and isinstance(raw.get('output'), list):
        for item in raw['output']:
            if not isinstance(item, dict) or not isinstance(item.get('content'), list):
                continue
            for part in item['content']:
                if isinstance(part, dict) and part.get('type') == 'output_text' and isinstance(part.get('text'), str):
                    texts.append(part['text'])
    return '\n'.join(texts) if texts else '文章として表示できる応答がありません。状態と下の全項目を確認してください。'


def _text_block(value: Any) -> str:
    """質問・回答にMarkdownやHTMLがあっても、記録の構造を変えず原文として表示する。"""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return '<pre>' + escape(text) + '</pre>'


def save_records(records: list[dict], path: str | Path) -> None:
    """明示操作で新しいファイルへ保存。同名上書きで初期記録を失わない。"""
    _unique_records(records)
    p = Path(path)
    if p.suffix not in {".jsonl", ".md"}:
        raise ValidationError("保存形式は.mdまたは.jsonlです。")
    if p.suffix == ".jsonl":
        content = "".join(record_json(r) + "\n" for r in records)
    else:
        lines = ["# 個人の読解記録", "", "生出力と本人の説明を区別。共有前に内容を確認してください。", ""]
        for number, r in enumerate(records, 1):
            cost = ('外部APIなし' if r['cost_kind'] == 'not_applicable' else
                    str(r['cost_value']) + ' USD' if r['cost_value'] is not None else '不明（0 USDとは扱わない）')
            # 記録の内部IDと、学生が読む活動名を分ける。
            activity = ACTIVITY_NAMES.get(r['activity_id'], str(r['activity_id']))
            model = r['reported_model'] or r['requested_model'] or ('AIなし' if r['service'] in {None, 'none'} else '不明')
            status = {'manual': '本人が記入', 'success': '応答完了', 'failed': '失敗',
                      'incomplete': '未完了', 'draft': '記入途中', 'pending': '処理中'}.get(r['status'], str(r['status']))
            mode = {'new': '新規', 'continue': '履歴を継続', None: '該当なし'}.get(r['conversation_mode'], str(r['conversation_mode']))
            lines += [f"## 記録 {number}: {escape(activity)}", "",
                      f"- 状態: {escape(status)}",
                      f"- モデル: {escape(str(model))}",
                      f"- 会話: {escape(mode)} / 過去の対話 {r['prior_turn_count'] or 0} 回",
                      f"- 費用: {cost}", ""]
            bibliography = r.get('bibliography')
            if isinstance(bibliography, dict) and bibliography.get('title'):
                lines += ['資料: ' + escape(str(bibliography['title'])), '']
            if r.get('error_message'):
                lines += ['### エラー・未完了の理由', '', _text_block(r['error_message']), '']
            for field, label in [('prompt', '送った質問'), ('input_scope', '送った資料の範囲'),
                                 ('student_explanation', '本人の説明'), ('evidence_location', '根拠の場所'),
                                 ('student_revision', '修正した説明'), ('unresolved_point', '残る疑問'),
                                 ('next_change', '次に変えること'), ('change_reason', '変更した理由')]:
                if r.get(field) is not None:
                    lines += ['### ' + label, '', _text_block(r[field]), '']
            lines += ['### AIの生回答', '', _text_block(_readable_response(r['response_raw'])), '']
        lines += ["## 再読込み用の全項目", "", '<details>', '<summary>入力・履歴・添付を含む全項目（再読込み時はこの部分を変更しない）</summary>', '',
                  "<!-- SEMINAR_RECORDS -->", "```json", record_json(records, indent=2),
                  "```", "<!-- END_SEMINAR_RECORDS -->", '', '</details>', '']
        content = "\n".join(lines)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f:
        f.write(content)


def load_records(path: str | Path) -> list[dict]:
    """未知の追加フィールドを含め、そのまま再読込みする。"""
    p = Path(path)
    content = p.read_text(encoding="utf-8")
    if p.suffix == ".jsonl":
        records = [_read_json(s) for s in content.splitlines() if s.strip()]
    elif p.suffix == ".md":
        start = "<!-- SEMINAR_RECORDS -->\n```json\n"
        end = "\n```\n<!-- END_SEMINAR_RECORDS -->"
        if content.count(start) != 1 or content.count(end) != 1:
            raise ValidationError("再読込み用の記録は1か所にまとめてください。欠落・重複した範囲を無視して読みません。")
        if end not in content.split(start, 1)[1]:
            raise ValidationError("再読込み用の記録が見つかりません。元のMarkdownを確認してください。")
        records = _read_json(content.split(start, 1)[1].split(end, 1)[0])
    else:
        raise ValidationError("読込み形式は.mdまたは.jsonlです。")
    _unique_records(records)
    return records

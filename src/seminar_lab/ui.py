"""notebook用の表示と保存。共通課題に論文選択欄を作らない。"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4
from .config import ACTIVITY_NAMES, material_context
from .records import save_records


def activity_description(course: dict, manifest: dict, activity_id: str) -> str:
    """授業で読む範囲と問いを、日本語の短い案内として表示する。"""
    view = activity_view(course, manifest, activity_id)
    lines = [ACTIVITY_NAMES.get(activity_id, activity_id)]
    if 'choices' in view:
        return '\n'.join(lines + ['論文の対象条件と入力条件を確認して選びます。'])
    context = material_context(course, manifest, activity_id, for_input=False)
    bibliography = context.get('bibliography') or {}
    title = bibliography.get('title', '') if isinstance(bibliography, dict) else str(bibliography)
    lines += ['資料: ' + title, '版: ' + str(view.get('source_version'))]
    scope = view.get('assigned_scope') or {}
    if isinstance(scope, dict):
        for field, label in [('pdf_pages', 'PDFのページ'), ('text_sections', '本文'),
                             ('figures', '図'), ('captions', '図注')]:
            if scope.get(field):
                lines.append(label + ': ' + ' / '.join(map(str, scope[field])))
    else:
        lines.append('読む範囲: ' + str(scope))
    for number, question in enumerate(view.get('questions') or [], 1):
        lines.append(f'{number}. {question}')
    return '\n'.join(lines)


def activity_view(course: dict, manifest: dict, activity_id: str) -> dict:
    """共通課題は固定参照を表示し、Homeworkだけ選択肢を示す。"""
    a = course["activities"][activity_id]
    if a.get("material_choice"):
        return {"activity_id": activity_id, "choices": ["対象条件を満たす教員追加論文", "学生選定U_<local_id>"],
                "journal_policy": course.get('homework_policy'), "phase": a["phase"]}
    context = material_context(course, manifest, activity_id, for_input=False)
    return {"activity_id": activity_id, "material_id": context["material_id"], "source_version": context.get("source_version"),
            "assigned_scope": context.get("assigned_scope"), "adoption": context["adoption"],
            "questions": course["question_sets"].get(context.get("question_set_id"), []), "phase": a.get("phase")}


def preview_payload(payload: dict) -> dict:
    """全送信履歴を表示。画像/PDFの長いbase64部分だけ表示上省略する。"""
    result = deepcopy(payload)
    for item in result.get("input", []):
        if not isinstance(item.get("content"), list):
            continue
        for content in item["content"]:
            for key in ("image_url", "file_data"):
                value = content.get(key)
                if isinstance(value, str) and value.startswith("data:"):
                    content[key] = value.split(";", 1)[0] + ";base64,(表示のみ省略。送信データは元のまま)"
    return result


def preview_text(payload: dict) -> str:
    """全文の質問と履歴を段落で表示する。省略するのは添付の符号化データだけ。"""
    visible = preview_payload(payload)
    lines = ['モデル: ' + visible['model'], '回答の上限: ' + str(visible['max_output_tokens']) + 'トークン']
    for key in ('temperature', 'top_p', 'reasoning'):
        if key in visible:
            lines.append(key + ': ' + str(visible[key]))
    lines.append('この後に並ぶ内容をすべて送信します。履歴の自動切捨てはしません。')
    for number, message in enumerate(visible['input'], 1):
        role = {'user': '自分から送る内容', 'assistant': '過去のAI回答'}.get(message.get('role'), '応答の公開メタデータ')
        lines += ['', f'--- {number}. {role} ---']
        if isinstance(message.get('content'), list):
            for part in message['content']:
                if isinstance(part.get('text'), str):
                    lines.append(part['text'])
                else:
                    lines.append(json.dumps(part, ensure_ascii=False))
        else:
            lines.append(json.dumps(message, ensure_ascii=False))
    return '\n'.join(lines)


def save_pair(records: list[dict], directory: str | Path = "outputs") -> tuple[Path, Path]:
    """手元へ保存する。サーバへ自動転送しない。"""
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    paths = tuple(Path(directory) / (suffix + ext) for ext in (".jsonl", ".md"))
    for path in paths:
        save_records(records, path)
    return paths

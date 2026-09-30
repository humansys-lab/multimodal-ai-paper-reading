"""notebook用の表示と保存。共通課題に論文選択欄を作らない。"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .config import material_context
from .records import save_records


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


def save_pair(records: list[dict], directory: str | Path = "outputs") -> tuple[Path, Path]:
    """手元へ保存する。サーバへ自動転送しない。"""
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    paths = tuple(Path(directory) / (suffix + ext) for ext in (".jsonl", ".md"))
    for path in paths:
        save_records(records, path)
    return paths

"""教員が用意した接続設定を読む。キーの読込み・送信・許可の自動発行はしない。"""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .client import LivePermission
from .config import ValidationError, load_yaml, validate_runtime


def load_connection(path: str | Path, permissions: dict[str, LivePermission]) -> tuple[dict, LivePermission]:
    """設定を検証し、同じ許可の再読込みでは消費済みの回数を保持する。"""
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

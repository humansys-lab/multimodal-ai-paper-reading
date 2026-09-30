"""公開候補の静的点検。公開許可・目視・Git過去履歴の監査を代替しない。"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
                   re.compile(r"gh[pousr]_[A-Za-z0-9]{25,}")]


def candidate_paths() -> list[Path]:
    """Git追跡候補と追跡済みを取得。ignoreされた元資料や秘密を読まない。"""
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / s for s in set(result.stdout.decode().split("\0")) if s]


def check(paths: list[Path]) -> list[str]:
    """秘密らしい内容を値を出さずに報告する。"""
    errors = []
    for path in paths:
        name = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        if path.is_symlink():
            errors.append(f"{name}: シンボリックリンクを公開候補に含めないでください。")
            continue
        if path.name.startswith(".env") or "runtime.local" in path.name or path.suffix in {".log", ".sqlite3", ".jsonl", ".pdf", ".pptx"} or set(path.parts) & {"outputs", "local_inputs", "private"}:
            errors.append(f"{name}: 私的資料・未承認バイナリが公開候補にあります。")
            continue
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                errors.append(f"{name}: 秘密情報らしい内容を検出（値は表示しません）。")
    return errors


def main() -> int:
    """静的点検を実行する。個人情報は別途目視が必要。"""
    errors = check(candidate_paths())
    print("\n".join(errors) if errors else "public static scan: pass (公開許可・個人情報の目視確認は別途必要)")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())

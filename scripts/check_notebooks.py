"""形式・Python構文・出力除去と、任意の通信禁止実行。Colab実機試験とは別。"""
import argparse
import contextlib
import io
from pathlib import Path
import socket
import sys
from types import ModuleType
from unittest.mock import patch
import nbformat


def inspect_notebook(path: Path, execute: bool = False) -> list[str]:
    """一つのnotebookをAPIなしで検査する。"""
    errors = []
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    module = ModuleType("__notebook_offline__")
    namespace = module.__dict__
    for n, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        if cell.outputs or cell.execution_count is not None:
            errors.append(f"{path.name}:{n}: 公開用出力が残っています。")
        code = compile(cell.source, f"{path.name}:{n}", "exec")
        if execute:
            with patch.dict(sys.modules, {module.__name__: module}), patch.object(socket.socket, "connect", side_effect=RuntimeError("offline test: network forbidden")), contextlib.redirect_stdout(io.StringIO()):
                exec(code, namespace)
    return errors


def main() -> int:
    """公開notebookをまとめて検査する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-offline", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors = []
    paths = sorted((root / "notebooks").glob("*.ipynb"))
    if len(paths) < 3:
        errors.append("00～02が不足しています。")
    for p in paths:
        errors.extend(inspect_notebook(p, args.execute_offline))
    print("\n".join(errors) if errors else f"notebooks: pass ({len(paths)} files; offline_execution={args.execute_offline})")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())

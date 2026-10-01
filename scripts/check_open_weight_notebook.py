"""03の実セルを明示した装置で実行する。API不要、初回のみモデル取得が必要。"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import platform
from time import monotonic


def replace_once(source: str, before: str, after: str) -> str:
    """試験で変更する入力が一つだけ存在することを確かめる。"""
    if source.count(before) != 1:
        raise ValueError(f"Notebookの試験入力が変わっています: {before}")
    return source.replace(before, after, 1)


def run(root: Path, output: Path, device: str, allow_download: bool) -> dict:
    """人工例で実セルを通す。回答の正答率やColab動作の判定はしない。"""
    notebook = json.loads((root / "notebooks/03_open_weight_lab.ipynb").read_text())
    namespace = {"ROOT": root}
    started = monotonic()
    executed = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        if "DEVICE = 'cuda'" in source:
            source = replace_once(source, "DEVICE = 'cuda'", f"DEVICE = {device!r}")
            source = replace_once(source, "ALLOW_DOWNLOAD = False", f"ALLOW_DOWNLOAD = {allow_download!r}")
        for flag in ("LOAD_MODEL", "OBSERVE", "PREVIEW", "RUN", "SAVE"):
            if f"{flag} = False" in source:
                source = replace_once(source, f"{flag} = False", f"{flag} = True")
        if "PROMPT = ''" in source:
            source = replace_once(source, "PROMPT = ''", "PROMPT = '机にペンが2本あります。3本追加すると何本ですか。数字だけで答えてください。'")
        if "save_result(globals().get('result'), annotations, ROOT)" in source:
            source = replace_once(source, "save_result(globals().get('result'), annotations, ROOT)",
                                  f"save_result(globals().get('result'), annotations, Path({str(output)!r}))")
        print(f"実セル {index} を実行", flush=True)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            exec(compile(source, f"03_open_weight_lab.ipynb:{index}", "exec"), namespace)
        (output / f"cell-{index:02d}.txt").write_text(captured.getvalue())
        executed.append(index)
    result = namespace["result"]
    probability_sum = float(namespace["probabilities"].sum().cpu())
    top5_sum = float(namespace["values"].sum().cpu())
    # 語彙全体のfloat32演算では合計に丸め誤差がある。
    # 表示値を改変せず、CPUのfloat64計算でも分布を照合する。
    torch = namespace["torch"]
    reference = torch.softmax(namespace["logits"].cpu().double(), dim=-1)
    observed = namespace["probabilities"].cpu().double()
    distribution_agrees = torch.allclose(observed, reference, rtol=1e-3, atol=1e-7)
    shape = list(namespace["vectors"].shape)
    parameters = sum(p.numel() for p in namespace["model"].parameters())
    checks = {
        "nine_code_cells": len(executed) == 9,
        "selected_device": namespace["model"].device.type == device,
        "parameter_count": parameters == 596049920,
        "embedding_shape": shape == [len(namespace["ids"]), 1024],
        "token_roundtrip": namespace["tokenizer"].decode(namespace["ids"]) == namespace["TEXT"],
        "probability_sum": abs(probability_sum - 1) < 1e-3,
        "probability_reference": distribution_agrees,
        "top5_probability_sum": 0 < top5_sum <= 1,
        "generation_status": result["status"] in {"completed", "output_limit"},
        "result_saved": json.loads(namespace["paths"][0].read_text()) == result,
    }
    receipt = {"status": "pass" if all(checks.values()) else "fail",
               "at": datetime.now(timezone.utc).isoformat(),
               "environment": platform.platform(), "python": platform.python_version(),
               "elapsed_seconds": round(monotonic() - started, 3),
               "device": device, "allow_download": allow_download,
               "checks": checks, "code_cell_indices": executed,
               "parameter_count": parameters, "embedding_shape": shape,
               "probability_sum": probability_sum, "top5_probability_sum": top5_sum,
               "float64_probability_sum": float(reference.sum()),
               "max_probability_difference": float((observed - reference).abs().max()),
               "result": result,
               "scope": "実セルの技術的な実行・保存。正答率・Colab T4の動作を保証しない。"}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    if not all(checks.values()):
        raise RuntimeError(f"実セルの検証に失敗: {checks}")
    return receipt


def main() -> int:
    """再現試験は既存の結果を上書きせず、新しい出力先へ保存する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, choices=("cpu", "mps", "cuda"))
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("build/open-weight-notebook-check"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (root / args.output).resolve()
    if not output.is_relative_to(root / "build"):
        parser.error("出力先はこの教材のbuildフォルダ内にしてください。")
    output.mkdir(parents=True, exist_ok=False)
    try:
        result = run(root, output, args.device, args.allow_download)
    except Exception as error:
        (output / "failure.json").write_text(json.dumps({"status": "fail", "error_type": type(error).__name__}))
        raise
    print("実セル検証:", result["status"], "生成状態:", result["result"]["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

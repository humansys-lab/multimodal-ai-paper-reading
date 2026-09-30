"""構造検査と配布ゲート。APIを呼ばない。"""
import argparse
from pathlib import Path
from seminar_lab.config import ValidationError, check_course, load_yaml, validate_runtime


def main() -> int:
    """不足を表示し、配布未準備は終了コード1で返す。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["structure", "readiness"], default="structure")
    parser.add_argument("--runtime", type=Path, help="非公開の実測済み実行設定。内容は表示しません。")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors = check_course(load_yaml(root / "config/course.yaml"), load_yaml(root / "materials/manifest.yaml"), root, args.mode)
    if args.mode == "readiness":
        if args.runtime is None:
            errors.append("配布未準備: --runtimeで実測済み設定の検査が必要です。")
        else:
            try:
                validate_runtime(load_yaml(args.runtime), {"text", "image", "pdf"}, {"max_output_tokens": 400})
            except (ValidationError, OSError):
                errors.append("配布未準備: 実行設定が未完了または読込み不能です。")
    for error in errors:
        print(error)
    print(f"{args.mode}: {'fail' if errors else 'pass'}")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())

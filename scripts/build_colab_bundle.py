"""秘密・原資料を含めず、公開前Colab試験用の小さなZIPを作る。"""
from pathlib import Path
import zipfile


def main() -> None:
    """必要なコード・空設定・ガイド・notebookだけを許可リストで梱包する。"""
    root = Path(__file__).resolve().parents[1]
    names = ["requirements-colab.txt", "requirements-open-weight.txt", "config/course.yaml", "config/runtime.example.yaml", "materials/manifest.yaml", "docs/api_usage.md", "docs/open_weight.md", "docs/troubleshooting.md", "docs/notebook_guide.md", "docs/lecture_references.md"]
    for folder, pattern in [("src/seminar_lab", "*.py"), ("notebooks", "*.ipynb"), ("materials", "**/*.md"), ("worksheets", "*.md")]:
        names.extend(p.relative_to(root).as_posix() for p in (root / folder).glob(pattern))
    target = root / "build/seminar-colab.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(names)):
            archive.write(root / name, "seminar/" + name)
    print(f"Colab試験用ZIPを作成: {target.name} ({len(set(names))} files)")


if __name__ == "__main__":
    main()

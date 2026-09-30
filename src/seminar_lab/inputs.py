"""明示した画像・PDF範囲を準備し、元ページとの対応を保存する。"""
from __future__ import annotations
import base64
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from .config import ValidationError


def _image_metadata(data: bytes) -> tuple[str, tuple[int, int]]:
    """画像の本体まで検査する。JPEGのverifyだけでは欠損を検出できない。"""
    if len(data) > 10_000_000:
        raise ValidationError("演習用の画像上限10MBを超えています。明示的に入力を見直してください。")
    try:
        with Image.open(BytesIO(data)) as im:
            kind, size = im.format, im.size
            if kind not in {"PNG", "JPEG"}:
                raise ValidationError("この実装はPNG/JPEGのみ対応します。自動変換は行いません。")
            im.verify()
        with Image.open(BytesIO(data)) as im:
            im.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("画像の本体を読み込めません。変換・補修せず停止しました。元ファイルを確認してください。") from None
    return kind, size


def _pdf_reader(data: bytes) -> PdfReader:
    """送るPDFを構造・暗号化・ページまで確認し、暗黙に補修しない。"""
    if len(data) > 20_000_000:
        raise ValidationError("演習用のPDF上限20MBを超えています。")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValidationError("暗号化PDFは入力できません。教員へ相談してください。")
        if not reader.pages:
            raise ValidationError("PDFにページがありません。")
        return reader
    except PdfReadError:
        raise ValidationError("PDFの構造を読み込めません。自動補修せず停止しました。元ファイルを確認してください。") from None


@dataclass(frozen=True)
class PreparedInput:
    """送信用内容と、学生が確認する由来情報。ローカルパスは記録しない。"""
    kind: str
    content: dict[str, Any]
    provenance: dict[str, Any]

    def validate(self) -> None:
        """表示する入力種別と実送信データが一致することを確認する。"""
        schemas = {
            "text": ("input_text", {"type", "text"}),
            "image": ("input_image", {"type", "image_url"}),
            "pdf": ("input_file", {"type", "filename", "file_data"}),
        }
        if self.kind not in schemas or not isinstance(self.content, dict) or not isinstance(self.provenance, dict):
            raise ValidationError("入力種別または由来情報が不正です。")
        expected, keys = schemas[self.kind]
        if set(self.content) != keys or self.content.get("type") != expected:
            raise ValidationError("表示する入力種別と送信データが一致しません。")
        if self.kind == "text" and (not isinstance(self.content["text"], str) or not self.content["text"].strip()):
            raise ValidationError("空の入力文は送信できません。")
        if self.kind in {"image", "pdf"}:
            value = self.content["image_url" if self.kind == "image" else "file_data"]
            prefixes = ("data:image/png;base64,", "data:image/jpeg;base64,") if self.kind == "image" else ("data:application/pdf;base64,",)
            if not isinstance(value, str) or not value.startswith(prefixes):
                raise ValidationError("添付の形式が不正です。自動変換・外部URLへの切替は行いません。")
            try:
                data = base64.b64decode(value.split(",", 1)[1], validate=True)
            except (ValueError, TypeError):
                raise ValidationError("添付のbase64データが不正です。") from None
            if not data:
                raise ValidationError("空の添付は送信できません。")
            if self.kind == "image":
                kind, _ = _image_metadata(data)
                mime = {"PNG": "image/png", "JPEG": "image/jpeg"}[kind]
                if not value.startswith(f"data:{mime};base64,"):
                    raise ValidationError("画像の種類と送信する形式名が一致しません。")
            else:
                _pdf_reader(data)
                filename = self.content["filename"]
                if not isinstance(filename, str) or not filename.endswith(".pdf") or any(c in filename for c in ("/", "\\", "\n", "\r")):
                    raise ValidationError("PDFの送信用ファイル名が不正です。ローカルのパスは送信できません。")


def text_input(text: str, location: str | None = None) -> PreparedInput:
    """貼り付けた文章をそのまま準備する。"""
    if not text.strip():
        raise ValidationError("入力文を記入してください。")
    return PreparedInput("text", {"type": "input_text", "text": text},
                         {"input_scope": location, "file_hash": sha256(text.encode()).hexdigest(), "transformation": "pasted_text"})


def image_input(path: str | Path, source_location: str, crop_description: str | None = None) -> PreparedInput:
    """PNG/JPEGを再変換せず入力する。切り出しの元位置は学生が記入する。"""
    if not source_location.strip():
        raise ValidationError("画像の元ページ・図を記入してください。")
    data = Path(path).read_bytes()
    kind, size = _image_metadata(data)
    mime = {"PNG": "image/png", "JPEG": "image/jpeg"}[kind]
    return PreparedInput("image", {"type": "input_image", "image_url": f"data:{mime};base64," + base64.b64encode(data).decode()},
                         {"file_hash": sha256(data).hexdigest(), "input_scope": source_location, "crop_description": crop_description,
                          "pixels": list(size), "transformation": "none", "byte_count": len(data)})


def pdf_input(path: str | Path, pages: list[int], page_labels: dict[int, str] | None = None) -> PreparedInput:
    """選んだ物理ページをPDFとして抽出する。OCR・画像化・本文のみへの変換はしない。"""
    data = Path(path).read_bytes()
    reader = _pdf_reader(data)
    if not pages or any(type(p) is not int or not 1 <= p <= len(reader.pages) for p in pages) or pages != sorted(set(pages)):
        raise ValidationError("PDFの実ページを1始まり、重複なしの昇順で指定してください。")
    writer = PdfWriter()
    for p in pages:
        writer.add_page(reader.pages[p - 1])
    buffer = BytesIO()
    writer.write(buffer)
    selected = buffer.getvalue()
    return PreparedInput("pdf", {"type": "input_file", "filename": "selected-pages.pdf",
                                 "file_data": "data:application/pdf;base64," + base64.b64encode(selected).decode()},
                         {"file_hash": sha256(data).hexdigest(), "selected_hash": sha256(selected).hexdigest(),
                          "input_scope": {"pdf_pages": pages}, "page_mapping": [
                              {"sent_page": i + 1, "source_pdf_page": p, "printed_label": (page_labels or {}).get(p)} for i, p in enumerate(pages)],
                          "transformation": "selected_pages_as_pdf", "byte_count": len(selected)})

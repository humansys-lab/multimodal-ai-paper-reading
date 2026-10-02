from pathlib import Path
import base64
from io import BytesIO
import importlib.util
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from seminar_lab.inputs import PreparedInput, pdf_input, image_input
from seminar_lab.config import ValidationError

ROOT=Path(__file__).resolve().parents[1]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def test_page_selection_mapping_and_hash(tmp_path):
    f=tmp_path/'fixture.pdf';w=PdfWriter()
    for width in [100,200,300]:w.add_blank_page(width,height=100)
    w.write(f)
    inp=pdf_input(f,[1,3],{1:'i',3:'2'})
    assert inp.provenance['page_mapping'][1]=={'sent_page':2,'source_pdf_page':3,'printed_label':'2'}
    selected=PdfReader(BytesIO(base64.b64decode(inp.content['file_data'].split(',')[1])))
    assert len(selected.pages)==2 and selected.pages[1].mediabox.width==300
    assert inp.provenance['file_hash']!=inp.provenance['selected_hash']
    for bad in [[],[0],[4],[2,1],[1,1],[True]]:
        with pytest.raises(ValidationError):pdf_input(f,bad)


def test_image_crop_provenance_without_conversion(tmp_path):
    f=tmp_path/'fixture.png';Image.new('RGB',(10,20),'white').save(f)
    inp=image_input(f,'fixture Fig. 1 / p1','left half')
    assert inp.provenance['pixels']==[10,20] and inp.provenance['crop_description']=='left half'
    assert base64.b64decode(inp.content['image_url'].split(',')[1])==f.read_bytes()
    with pytest.raises(ValidationError):image_input(f,'')


def test_notebooks_offline_default_execution():
    checker=module('check_notebooks')
    for p in (ROOT/'notebooks').glob('*.ipynb'):
        assert checker.inspect_notebook(p,execute=True)==[]


def test_public_scan_and_secret_detection(tmp_path):
    checker=module('check_public_release')
    assert checker.check(checker.candidate_paths())==[]
    secret=tmp_path/'leak.txt';secret.write_text('sk-'+'a'*30)
    result=checker.check([secret])
    assert result and 'a'*30 not in str(result)


def test_local_connection_file_is_not_public_even_without_a_key(tmp_path):
    private = tmp_path / 'connection.local.yaml'
    private.write_text('runtime: {}\npermission: {}\n')
    assert module('check_public_release').check([private])


def test_damaged_pdf_is_rejected_without_automatic_repair(tmp_path):
    import re
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    # 人工PDFの索引位置を1バイトずらし、既定の寛容な読込みなら補修される破損を作る。
    damaged = re.sub(rb'(startxref\s+)(\d+)', lambda m: m[1] + str(int(m[2]) + 1).encode(), buffer.getvalue())
    path = tmp_path / 'damaged.pdf'
    path.write_bytes(damaged)
    with pytest.raises(ValidationError, match='自動補修せず'):
        pdf_input(path, [1])
    assert path.read_bytes() == damaged


def test_truncated_jpeg_body_is_rejected_without_conversion(tmp_path):
    path = tmp_path / 'incomplete.jpg'
    buffer = BytesIO()
    Image.new('RGB', (64, 64), 'blue').save(buffer, format='JPEG')
    damaged = buffer.getvalue()[:-20]
    # JPEGのヘッダ検査は成功するが、本体の展開で欠損が分かる例。
    Image.open(BytesIO(damaged)).verify()
    path.write_bytes(damaged)
    with pytest.raises(ValidationError, match='本体を読み込めません'):
        image_input(path, 'test fixture')
    assert path.read_bytes() == damaged


def test_prepared_image_requires_matching_mime_and_decodable_body(tmp_path):
    path = tmp_path / 'valid.png'
    Image.new('RGB', (12, 16), 'green').save(path)
    valid = image_input(path, 'test fixture')
    valid.validate()
    mislabeled = {**valid.content, 'image_url': valid.content['image_url'].replace('image/png', 'image/jpeg')}
    with pytest.raises(ValidationError, match='形式名が一致しません'):
        PreparedInput('image', mislabeled, valid.provenance).validate()
    not_image = {'type': 'input_image', 'image_url': 'data:image/png;base64,' + base64.b64encode(b'not an image').decode()}
    with pytest.raises(ValidationError, match='本体を読み込めません'):
        PreparedInput('image', not_image, {}).validate()


def test_prepared_pdf_requires_valid_body_and_safe_filename(tmp_path):
    path = tmp_path / 'valid.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(path)
    valid = pdf_input(path, [1])
    valid.validate()
    for filename in ['/private/document.pdf', 'private\\document.pdf', 'file.pdf\n', None]:
        with pytest.raises(ValidationError, match='ファイル名が不正'):
            PreparedInput('pdf', {**valid.content, 'filename': filename}, valid.provenance).validate()
    corrupted = {**valid.content, 'file_data': 'data:application/pdf;base64,' + base64.b64encode(b'%PDF-1.7\ninvalid\n%%EOF').decode()}
    with pytest.raises(ValidationError, match='自動補修せず'):
        PreparedInput('pdf', corrupted, valid.provenance).validate()


@pytest.mark.parametrize('kind,limit', [('image', 10_000_000), ('pdf', 20_000_000)])
def test_oversized_source_is_rejected_before_reading_bytes(tmp_path, monkeypatch, kind, limit):
    path = tmp_path / ('large.' + kind)
    with path.open('wb') as handle:
        handle.truncate(limit + 1)
    def forbidden_read(*args, **kwargs):
        raise AssertionError('Oversized source must not be read into memory')
    monkeypatch.setattr(Path, 'read_bytes', forbidden_read)
    with pytest.raises(ValidationError, match='上限'):
        image_input(path, 'test fixture') if kind == 'image' else pdf_input(path, [1])


@pytest.mark.parametrize('name', ['', 'missing.png'])
def test_missing_input_file_has_classroom_instruction(tmp_path, name):
    with pytest.raises(ValidationError, match='Files欄'):
        image_input(tmp_path / name, 'test fixture')


@pytest.mark.parametrize('width,height', [(8000, 5000), (20000, 20000)])
def test_huge_pixel_dimensions_stop_before_image_decode(tmp_path, width, height):
    import struct
    import zlib
    path = tmp_path / 'huge.png'
    buffer = BytesIO()
    Image.new('RGB', (1, 1)).save(buffer, format='PNG')
    data = bytearray(buffer.getvalue())
    # Small artificial PNG with a valid header CRC but excessive declared dimensions.
    data[16:24] = struct.pack('>II', width, height)
    data[29:33] = struct.pack('>I', zlib.crc32(data[12:29]))
    path.write_bytes(data)
    with pytest.raises(ValidationError, match='画素'):
        image_input(path, 'test fixture')


def test_png_selected_as_pdf_has_actionable_error(tmp_path):
    path = tmp_path / 'wrong-input.png'
    Image.new('RGB', (10, 10), 'blue').save(path)
    with pytest.raises(ValidationError, match='input_kind'):
        pdf_input(path, [1])

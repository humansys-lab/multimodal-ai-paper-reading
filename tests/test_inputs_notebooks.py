from pathlib import Path
import base64
from io import BytesIO
import importlib.util
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from seminar_lab.inputs import pdf_input, image_input
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

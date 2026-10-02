"""埋込み関数を含む実Notebookで、入力例と保存・停止条件を検査する。"""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch
from uuid import uuid4
import pytest

ROOT = Path(__file__).resolve().parents[1]


def book_namespace(filename, folder, monkeypatch):
    notebook = json.loads((ROOT/'notebooks'/filename).read_text())
    module = ModuleType('standalone_' + uuid4().hex)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.chdir(folder)
    with contextlib.redirect_stdout(io.StringIO()):
        for c in notebook['cells']:
            if c['cell_type'] == 'code':
                exec(compile(''.join(c['source']), filename, 'exec'), module.__dict__)
    return module.__dict__, notebook


def action(notebook, marker):
    cells = [''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code' and not c.get('metadata',{}).get('embedded_support') and marker in ''.join(c['source'])]
    assert len(cells) == 1
    return cells[0]


def test_manual_examples_save_without_repository(tmp_path, monkeypatch):
    ns, nb = book_namespace('00_setup.ipynb', tmp_path, monkeypatch)
    save = action(nb, 'annotations =').replace('SAVE = False','SAVE = True')
    exec(save.replace("'student_explanation': None", "'student_explanation': 'まだ説明できない箇所がある'"),ns)
    first = [p.read_bytes() for p in ns['paths']]
    old_paths = ns['paths']
    exec(action(nb, 'record_stage =').replace("record_stage = '朝：AIなしで読む'", "record_stage = '午後：説明し直す'"),ns)
    exec(save.replace("'student_explanation': None", "'student_explanation': '原文を確認して説明し直した'"),ns)
    records = ns['load_records'](ns['paths'][0])
    assert [r['phase'] for r in records] == ['R0','R3']
    assert records == ns['load_records'](ns['paths'][1])
    assert [p.read_bytes() for p in old_paths] == first
    assert all(r['response_raw'] is None for r in records)


@pytest.mark.parametrize('filename',['01_dialogue_lab.ipynb','02_document_lab.ipynb','03_open_weight_lab.ipynb'])
def test_embedded_common_contract_and_transfer_separation(filename,tmp_path,monkeypatch):
    ns,_=book_namespace(filename,tmp_path,monkeypatch)
    context=lambda aid,**kw: ns['material_context'](ns['course'],ns['manifest'],aid,for_input=False,**kw)
    first=context('P0')
    for aid in ['P1','P2a','P3']:
        value=context(aid)
        assert [value[k] for k in ['material_id','source_version','assigned_scope','question_set_id']] == [first[k] for k in ['material_id','source_version','assigned_scope','question_set_id']]
        with pytest.raises(ValueError,match='固定'):
            context(aid,selection='PRACTICE')
    assert context('TRANSFER')['phase']=='transfer'
    assert context('TRANSFER')['material_id']=='P02'
    assert context('PRACTICE')['phase']=='practice'
    assert context('PRACTICE')['material_id']!='P01'


def test_actual_document_example_resize_pdf_and_invalid_input(tmp_path,monkeypatch):
    ns,nb=book_namespace('02_document_lab.ipynb',tmp_path,monkeypatch)
    create=action(nb,'CREATE_EXAMPLE =').replace('CREATE_EXAMPLE = False','CREATE_EXAMPLE = True')
    exec(create,ns)
    png=tmp_path/'outputs/input-example/notebook-example.png'
    pdf=png.with_suffix('.pdf')
    assert ns['image_input'](png,'自作図').provenance['pixels']==[1200,600]
    small=ns['resized_image_input'](png,'自作図',600)
    assert small.provenance['pixels']==[600,300]
    selected=ns['pdf_input'](pdf,[1])
    selected.validate()
    assert selected.provenance['page_mapping'][0]['source_pdf_page']==1
    before=png.read_bytes()
    with pytest.raises(ValueError,match='作成済み'): exec(create,ns)
    assert png.read_bytes()==before
    ns['inputs']=[small]
    prepare=action(nb,'PREPARE_INPUT =').replace('PREPARE_INPUT = False','PREPARE_INPUT = True').replace("input_kind = 'image'","input_kind = 'pdf'").replace("local_path = ''",f'local_path = {str(pdf)!r}').replace('pdf_pages = []','pdf_pages = [0]')
    with pytest.raises(ValueError,match='1始まり'): exec(prepare,ns)
    assert ns['inputs']==[]


def test_embedded_dialogue_history_and_failure_are_not_normalized(tmp_path,monkeypatch,runtime):
    """人工応答はこの試験内だけ。公開Notebookは実際の送信経路だけを持つ。"""
    ns,_=book_namespace('01_dialogue_lab.ipynb',tmp_path,monkeypatch)
    session=ns['Session']()
    context=ns['material_context'](ns['course'],ns['manifest'],'PRACTICE')
    class TestTransport:
        def send(self,payload):
            return {'status':'completed','model':runtime['model'],'usage':None,'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'TEST FIXTURE ONLY'}]}]}
    args=dict(runtime=runtime,context=context,prompt='練習の問い',inputs=[],parameters={'max_output_tokens':100},transport=TestTransport())
    first=session.run(**args,mode='new',run_id='one')
    second=session.run(**args,mode='continue',run_id='two')
    assert first['status']==second['status']=='success'
    assert second['prior_turn_count']==1 and len(second['request_input'])==3
    with pytest.raises(ValueError,match='実行済み'):
        session.run(**args,mode='continue',run_id='two')
    history=deepcopy(session.history)
    class Broken:
        def send(self,payload): raise ns['TransportError']('network')
    failed=session.run(**{**args,'transport':Broken()},mode='continue',run_id='three')
    assert failed['status']=='failed' and failed['cost_value'] is None
    assert session.history==history
    paths=ns['save_pair'](session.records,tmp_path/'records')
    assert ns['load_records'](paths[0])==ns['load_records'](paths[1])==session.records

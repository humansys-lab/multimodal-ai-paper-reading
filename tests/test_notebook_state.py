"""教材セルの再実行で学生の記入や保存済み記録を失わないことを確認する。"""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]


def code_cell(name: str, marker: str) -> str:
    """指定した処理を含む実際のNotebookセルを読む。"""
    nb = json.loads((ROOT / 'notebooks' / name).read_text())
    cells = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and marker in ''.join(c['source'])]
    assert len(cells) == 1
    return cells[0]


@pytest.mark.parametrize('name', ['00_setup.ipynb', '01_dialogue_lab.ipynb', '02_document_lab.ipynb'])
def test_save_off_reexecution_preserves_student_explanation(name):
    record = {'student_explanation': '学生が記入した説明', 'unresolved_point': 'まだ残る問い'}
    original = record.copy()
    namespace = {'session': SimpleNamespace(records=[record]), 'offline_record': record}
    exec(code_cell(name, 'annotations ='), namespace)
    assert record == original


def test_save_without_execution_reports_missing_record(tmp_path):
    source = code_cell('01_dialogue_lab.ipynb', 'annotations =').replace('SAVE = False', 'SAVE = True')
    with pytest.raises(ValueError, match='実行記録がありません'):
        exec(source, {'session': SimpleNamespace(records=[]), 'ROOT': tmp_path})


def test_open_weight_save_refuses_to_overwrite_previous_record(tmp_path):
    source = code_cell('03_open_weight_lab.ipynb', 'destination.open').replace('SAVE = False', 'SAVE = True')
    namespace = {'ROOT': tmp_path, 'json': json, 'result': {'run_id': 'synthetic', 'response_raw': 'fixture'}}
    exec(source, namespace)
    target = tmp_path / 'outputs/open-weight/synthetic.json'
    before = target.read_bytes()
    namespace['result']['response_raw'] = 'changed'
    with pytest.raises(FileExistsError):
        exec(source, namespace)
    assert target.read_bytes() == before

"""教材セルの再実行で学生の記入や保存済み記録を失わないことを確認する。"""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]


def code_cell(name: str, marker: str) -> str:
    """指定した処理を含む実際のNotebookセルを読む。"""
    nb = json.loads((ROOT / 'notebooks' / name).read_text())
    cells = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and not c.get('metadata', {}).get('embedded_support') and marker in ''.join(c['source'])]
    assert len(cells) == 1
    # 操作セル単体の試験では共通実装を供給する。埋込みの同一性と単独実行は別に検査。
    prelude = f"""from seminar_lab import config as _config, records as _records, ui as _ui, inputs as _inputs, client as _client, open_weight as _local, connection as _connection
for _module in (_config, _records, _ui, _inputs, _client, _local, _connection):
    for _name, _value in vars(_module).items():
        if not _name.startswith('_'):
            globals().setdefault(_name, _value)
if 'course' not in globals(): course = _config.load_yaml(Path({str(ROOT)!r}) / 'config/course.yaml')
if 'manifest' not in globals(): manifest = _config.load_yaml(Path({str(ROOT)!r}) / 'materials/manifest.yaml')
"""
    # 保存だけの試験には授業設定は不要。選択・論文生成セルだけ読み込む。
    if 'record_stage =' not in cells[0] and 'reading_context = material_context' not in cells[0]:
        prelude = prelude.split("if 'course'")[0]
    return prelude + cells[0]


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


def test_open_weight_annotation_revision_keeps_previous_record(tmp_path, model_result):
    source = code_cell('03_open_weight_lab.ipynb', "save_result(globals().get('result'), annotations, ROOT)").replace('SAVE = False', 'SAVE = True')
    namespace = {'ROOT': tmp_path, 'json': json, 'result': {**model_result, 'response_raw': 'fixture'}}
    exec(source, namespace)
    target, = (tmp_path / 'outputs/open-weight').glob('*.json')
    before = target.read_bytes()
    source = source.replace("'student_explanation': None", "'student_explanation': '追記した説明'")
    exec(source, namespace)
    assert target.read_bytes() == before
    saved = sorted((tmp_path / 'outputs/open-weight').glob('*.json'))
    assert len(saved) == 2
    assert {json.loads(p.read_text())['response_raw'] for p in saved} == {'fixture'}
    assert namespace['result']['student_explanation'] == '追記した説明'

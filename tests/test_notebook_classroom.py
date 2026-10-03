"""Notebookの実セルを使い、授業中の再実行・条件変更・保存を検査する。"""
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image
from seminar_lab.client import Session, LivePermission
from seminar_lab.config import material_context
from seminar_lab.ui import preview_text
from test_notebook_state import code_cell

ROOT = Path(__file__).resolve().parents[1]


def test_permission_preview_does_not_consume_or_reset(runtime):
    permission = LivePermission('teacher', 'synthetic', runtime['route'], runtime['model'], 'test', 1, 2)
    permission.validate(runtime)
    assert permission.used == 0
    permission.consume(runtime)
    assert permission.used == 1
    assert permission.used == 1


def test_document_preparation_failure_clears_old_image(tmp_path):
    source = code_cell('02_document_lab.ipynb', 'PREPARE_INPUT =').replace('PREPARE_INPUT = False', 'PREPARE_INPUT = True')
    namespace = {'inputs': ['previous image']}
    with pytest.raises(ValueError):
        exec(source, namespace)
    assert namespace['inputs'] == []


def test_document_resize_previews_exact_sent_pixels(tmp_path):
    path = tmp_path / 'artificial.png'
    Image.new('RGB', (100, 60), 'blue').save(path)
    source = code_cell('02_document_lab.ipynb', 'PREPARE_INPUT =')
    assert "input_kind = 'pdf'" in source
    source = source.replace('PREPARE_INPUT = False', 'PREPARE_INPUT = True').replace("input_kind = 'pdf'", "input_kind = 'resized_image'")
    source = source.replace("local_path = ''", f'local_path = {str(path)!r}').replace("source_location = ''", "source_location = 'synthetic'").replace('width = 600', 'width = 50')
    namespace = {}
    exec(source, namespace)
    assert namespace['inputs'][0].provenance['pixels'] == [50, 30]
    assert namespace['inputs'][0].provenance['original_pixels'] == [100, 60]


def test_changed_question_requires_preview_before_key_prompt(adopted, runtime):
    course, manifest = adopted
    permission = LivePermission('teacher', 'synthetic', runtime['route'], runtime['model'], 'test', 1, 2)
    ns = dict(course=course, manifest=manifest, runtime=runtime, activity_id='L2', session=Session(),
              question='before', inputs=[], conversation_mode='new', parameters={'max_output_tokens':100},
              permission=permission, LivePermission=LivePermission, material_context=material_context,
              preview_text=preview_text, deepcopy=deepcopy, run_id='synthetic')
    exec(code_cell('01_dialogue_lab.ipynb', 'previewed_request = None'), ns)
    ns['question'] = 'after'
    with pytest.raises(ValueError, match='プレビュー'):
        exec(code_cell('01_dialogue_lab.ipynb', 'SEND =').replace('SEND = False', 'SEND = True'), ns)
    assert permission.used == 0 and ns['result'] is None


def test_save_does_not_annotate_previous_run_after_new_run_failure(tmp_path):
    record = {'run_id': 'old', 'student_explanation': 'keep'}
    ns = dict(session=SimpleNamespace(records=[record]), run_id='new', ROOT=tmp_path)
    with pytest.raises(ValueError, match='今回の実行記録'):
        exec(code_cell('01_dialogue_lab.ipynb', 'annotations =').replace('SAVE = False', 'SAVE = True'), ns)
    assert record['student_explanation'] == 'keep'


def test_failed_local_generation_cannot_save_old_answer(tmp_path):
    ns = dict(ROOT=tmp_path, result={'run_id':'old'}, source_excerpt='', source_location='', PROMPT='')
    with pytest.raises(ValueError, match='質問'):
        exec(code_cell('03_open_weight_lab.ipynb', 'RUN =').replace('RUN = False', 'RUN = True'), ns)
    assert ns['result'] is None
    with pytest.raises(ValueError, match='生成結果'):
        exec(code_cell('03_open_weight_lab.ipynb', "save_result(globals().get('result'), annotations, ROOT)").replace('SAVE = False', 'SAVE = True'), ns)
    assert not (tmp_path / 'outputs').exists()


def test_local_save_keeps_student_explanation_and_raw_output(tmp_path, model_result):
    result = {**model_result, 'response_raw':'raw','student_explanation':'mine','unresolved_point':'unknown'}
    ns = dict(ROOT=tmp_path, result=result.copy())
    exec(code_cell('03_open_weight_lab.ipynb', "save_result(globals().get('result'), annotations, ROOT)").replace('SAVE = False', 'SAVE = True'), ns)
    path, = (tmp_path / 'outputs/open-weight').glob('*.json')
    assert json.loads(path.read_text()) == result
    assert ns['result'] == result


def test_unassigned_local_observation_cannot_become_paper_record(tmp_path, model_result):
    ns = dict(ROOT=tmp_path, result={**model_result, 'response_raw': 'fixture', 'reading_context': None})
    exec(code_cell('03_open_weight_lab.ipynb', "save_result(globals().get('result'), annotations, ROOT)").replace('SAVE = False', 'SAVE = True'), ns)
    assert len(ns['paths']) == 1 and ns['paths'][0].suffix == '.json'
    assert not list((tmp_path / 'outputs').glob('*.jsonl'))


@pytest.mark.parametrize('marker', ['vectors = model.get_input_embeddings()', 'probabilities = torch.softmax'])
def test_changed_observation_text_requires_new_tokenization(marker):
    ns = dict(OBSERVE=True, TEXT='変更した文', observed_text='以前の文', ids=[1], model=object(), tokenizer=object())
    with pytest.raises(ValueError, match='トークン'):
        exec(code_cell('03_open_weight_lab.ipynb', marker), ns)


def test_local_prompt_preview_explains_missing_model():
    with pytest.raises(ValueError, match='LOAD_MODEL'):
        exec(code_cell('03_open_weight_lab.ipynb', 'PREVIEW =').replace('PREVIEW = False', 'PREVIEW = True'), {})


@pytest.mark.parametrize('case', ['missing', 'different_version', 'old_module_in_memory'])
def test_model_load_rejects_unverified_dependencies_before_loading(monkeypatch, case):
    """INSTALL忘れと、pip更新後に旧版がメモリへ残る状況を、重みの取得前に止める。"""
    import importlib.metadata
    import sys
    import seminar_lab.open_weight as local

    def installed_version(name):
        if case == 'missing':
            raise importlib.metadata.PackageNotFoundError(name)
        if case == 'different_version' and name == 'torch':
            return '2.9.0'
        return {'torch': '2.8.0', 'torchvision': '0.23.0', 'transformers': '4.57.6'}[name]

    monkeypatch.setattr(importlib.metadata, 'version', installed_version)
    monkeypatch.setattr(local, 'load_model', lambda *a, **kw: pytest.fail('未検証の依存ではモデルを取得・読込みしない'))
    if case == 'old_module_in_memory':
        monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(__version__='2.7.0'))
        monkeypatch.setitem(sys.modules, 'torchvision', SimpleNamespace(__version__='0.23.0'))
        monkeypatch.setitem(sys.modules, 'transformers', SimpleNamespace(__version__='4.57.6'))
    source = code_cell('03_open_weight_lab.ipynb', 'LOAD_MODEL =').replace('LOAD_MODEL = False', 'LOAD_MODEL = True')
    ns = {'model': 'previous', 'tokenizer': 'previous'}
    expected = 'INSTALL' if case != 'old_module_in_memory' else '再起動'
    with pytest.raises(ValueError, match=expected):
        exec(source, ns)
    assert ns['model'] is None and ns['tokenizer'] is None


def test_homework_blank_form_never_replaces_common_state(adopted):
    ns = dict(course=adopted[0], manifest=adopted[1], material_context=material_context, activity_id='P2a', run_id='keep')
    with pytest.raises(ValueError, match='素材を明示'):
        exec(code_cell('01_dialogue_lab.ipynb', 'START_HOMEWORK =').replace('START_HOMEWORK = False', 'START_HOMEWORK = True'), ns)
    assert ns['activity_id'] == 'P2a' and ns['run_id'] == 'keep'


def test_failed_document_send_clears_previous_result_before_key_input():
    ns = {'inputs': [], 'result': {'response_raw': 'previous'}}
    with pytest.raises(ValueError, match='画像またはPDF'):
        exec(code_cell('02_document_lab.ipynb', 'SEND =').replace('SEND = False', 'SEND = True'), ns)
    assert ns['result'] is None


def test_homework_without_selection_explains_setup_before_preview(runtime):
    ns = dict(question='問い', runtime=runtime, permission=object(), activity_id='HW1')
    with pytest.raises(ValueError, match='Homeworkの論文情報'):
        exec(code_cell('01_dialogue_lab.ipynb', 'previewed_request = None'), ns)


def test_repeated_run_is_rejected_before_asking_for_key(adopted, runtime, monkeypatch):
    from test_client_records import FakeTransport
    course, manifest = adopted
    permission = LivePermission('teacher', 'synthetic', runtime['route'], runtime['model'], 'test', 1, 2)
    session = Session()
    context = material_context(course, manifest, 'L2')
    session.run(runtime=runtime, context=context, prompt='問い', inputs=[], mode='new',
                parameters={'max_output_tokens':100}, run_id='used', transport=FakeTransport())
    ns = dict(course=course, manifest=manifest, runtime=runtime, activity_id='L2', session=session,
              question='問い', inputs=[], conversation_mode='new', parameters={'max_output_tokens':100},
              permission=permission, material_context=material_context,
              preview_text=preview_text, deepcopy=deepcopy, run_id='used')
    exec(code_cell('01_dialogue_lab.ipynb', 'previewed_request = None'), ns)
    monkeypatch.setattr('getpass.getpass', lambda *_: pytest.fail('実行済みならキー入力へ進まない'))
    with pytest.raises(ValueError, match='実行済み'):
        exec(code_cell('01_dialogue_lab.ipynb', 'SEND =').replace('SEND = False', 'SEND = True'), ns)
    assert permission.used == 0 and len(session.records) == 1


@pytest.mark.parametrize('name', ['01_dialogue_lab.ipynb', '02_document_lab.ipynb'])
def test_save_after_rejected_duplicate_never_changes_previous_answer(tmp_path, name):
    """送信セルがresultを消した後、同じ番号の古い記録へ説明を付けない。"""
    record = {'run_id': 'used', 'student_explanation': '前の問いについての説明'}
    ns = dict(session=SimpleNamespace(records=[record]), run_id='used', result=None, ROOT=tmp_path)
    source = code_cell(name, 'annotations =').replace('SAVE = False', 'SAVE = True')
    source = source.replace("'student_explanation': None", "'student_explanation': '送れなかった新しい問いの説明'")
    with pytest.raises(ValueError, match='今回の実行記録'):
        exec(source, ns)
    assert record['student_explanation'] == '前の問いについての説明'
    assert not (tmp_path / 'outputs').exists()


def test_manual_morning_and_final_explanations_remain_separate(tmp_path):
    """実際の00セルで朝→午後→朝を操作し、最初の説明と保存ファイルを保持する。"""
    ns = {'ROOT': ROOT}
    choose = code_cell('00_setup.ipynb', 'record_stage =')
    save = code_cell('00_setup.ipynb', 'annotations =').replace('SAVE = False', 'SAVE = True')
    exec(choose, ns)
    ns['ROOT'] = tmp_path
    exec(save.replace("'student_explanation': None", "'student_explanation': '朝の人工記録'"), ns)
    initial_paths = ns['paths']
    initial_bytes = [p.read_bytes() for p in initial_paths]
    morning = deepcopy(ns['offline_record'])
    ns['ROOT'] = ROOT
    exec(choose.replace("record_stage = '朝：AIなしで読む'", "record_stage = '午後：説明し直す'"), ns)
    ns['ROOT'] = tmp_path
    exec(save.replace("'student_explanation': None", "'student_explanation': '午後の人工記録'"), ns)
    records = list(ns['manual_records'].values())
    assert records[0] == morning
    assert [r['phase'] for r in records] == ['R0', 'R3']
    assert records[0]['run_id'] != records[1]['run_id']
    assert all(r['response_raw'] is None and r['service'] == 'none' for r in records)
    assert all(ns['load_records'](p) == records for p in ns['paths'])
    assert [p.read_bytes() for p in initial_paths] == initial_bytes
    ns['ROOT'] = ROOT
    exec(choose, ns)
    assert ns['offline_record'] == morning


def test_invalid_manual_stage_does_not_replace_morning_record():
    ns = {'ROOT': ROOT}
    choose = code_cell('00_setup.ipynb', 'record_stage =')
    exec(choose, ns)
    before = deepcopy(ns['manual_records'])
    with pytest.raises(ValueError, match='記録する段階'):
        exec(choose.replace("record_stage = '朝：AIなしで読む'", "record_stage = 'unknown'"), ns)
    assert ns['manual_records'] == before


def test_repeated_continue_stops_when_success_changed_the_preview(adopted, runtime, monkeypatch):
    """継続に成功すると履歴が増える。古いプレビューの再送もキー入力前に拒否する。"""
    from test_client_records import FakeTransport
    course, manifest = adopted
    permission = LivePermission('teacher', 'synthetic', runtime['route'], runtime['model'], 'test', 1, 2)
    session = Session()
    context = material_context(course, manifest, 'L2')
    session.run(runtime=runtime, context=context, prompt='最初の問い', inputs=[], mode='new',
                parameters={'max_output_tokens':100}, run_id='initial', transport=FakeTransport())
    ns = dict(course=course, manifest=manifest, runtime=runtime, activity_id='L2', session=session,
              question='続ける問い', inputs=[], conversation_mode='continue', parameters={'max_output_tokens':100},
              permission=permission, material_context=material_context,
              preview_text=preview_text, deepcopy=deepcopy, run_id='continued')
    exec(code_cell('01_dialogue_lab.ipynb', 'previewed_request = None'), ns)
    session.run(runtime=runtime, context=context, prompt=ns['question'], inputs=[], mode='continue',
                parameters=ns['parameters'], run_id='continued', transport=FakeTransport())
    before = deepcopy(session.records)
    monkeypatch.setattr('getpass.getpass', lambda *_: pytest.fail('古いプレビューならキー入力へ進まない'))
    with pytest.raises(ValueError, match='プレビュー'):
        exec(code_cell('01_dialogue_lab.ipynb', 'SEND =').replace('SEND = False', 'SEND = True'), ns)
    assert permission.used == 0 and session.records == before and ns['result'] is None


@pytest.mark.parametrize('case', ['ai_free_activity', 'unconfirmed_input'])
def test_local_paper_generation_checks_activity_before_computing(adopted, monkeypatch, case):
    """ローカル推論も、AIなしの段階や未確認資料を生成後の保存で初めて拒否しない。"""
    import seminar_lab.config as config
    import seminar_lab.open_weight as local
    course, approved = adopted
    selected_manifest = deepcopy(approved)
    if case == 'unconfirmed_input':
        next(m for m in selected_manifest['materials'] if m['id'] == 'P01')['rights']['ai_input'] = 'unconfirmed'
    monkeypatch.setattr(config, 'load_yaml', lambda path: course if path.name == 'course.yaml' else selected_manifest)
    monkeypatch.setattr(local, 'generate', lambda *a, **kw: pytest.fail('禁止された活動では推論を始めない'))
    ns = dict(ROOT=ROOT, PROMPT='人工的な操作確認', previewed_prompt='人工的な操作確認',
              source_excerpt='', source_location='', activity_id='P0' if case == 'ai_free_activity' else 'METHODS',
              tokenizer=object(), model=object(), result={'old': True})
    expected = 'AIなし' if case == 'ai_free_activity' else '確認待ち'
    with pytest.raises(ValueError, match=expected):
        exec(code_cell('03_open_weight_lab.ipynb', 'RUN =').replace('RUN = False', 'RUN = True'), ns)
    assert ns['result'] is None

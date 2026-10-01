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
    source = source.replace('PREPARE_INPUT = False', 'PREPARE_INPUT = True').replace("input_kind = 'image'", "input_kind = 'resized_image'")
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
        exec(code_cell('03_open_weight_lab.ipynb', 'from seminar_lab.open_weight import save_result').replace('SAVE = False', 'SAVE = True'), ns)
    assert not (tmp_path / 'outputs').exists()


def test_local_save_keeps_student_explanation_and_raw_output(tmp_path):
    result = {'run_id':'synthetic','response_raw':'raw','student_explanation':'mine','unresolved_point':'unknown'}
    ns = dict(ROOT=tmp_path, result=result.copy())
    exec(code_cell('03_open_weight_lab.ipynb', 'from seminar_lab.open_weight import save_result').replace('SAVE = False', 'SAVE = True'), ns)
    path, = (tmp_path / 'outputs/open-weight').glob('*.json')
    assert json.loads(path.read_text()) == result
    assert ns['result'] == result


def test_unassigned_local_observation_cannot_become_paper_record(tmp_path):
    ns = dict(ROOT=tmp_path, result={'run_id': 'synthetic', 'response_raw': 'fixture', 'reading_context': None})
    exec(code_cell('03_open_weight_lab.ipynb', 'from seminar_lab.open_weight import save_result').replace('SAVE = False', 'SAVE = True'), ns)
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

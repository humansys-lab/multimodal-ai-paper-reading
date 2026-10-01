"""明示した縮小とローカルモデルの共通記録。モデル推論の代用にはしない。"""
from copy import deepcopy
from hashlib import sha256
from PIL import Image
import pytest
from seminar_lab.inputs import resized_image_input
from seminar_lab.config import ValidationError, material_context
from seminar_lab.open_weight import MODEL_ID, REVISION, reading_record
from seminar_lab.records import save_records, load_records


def test_explicit_resize_preserves_original_and_records_sent_hash(tmp_path):
    path = tmp_path / 'source.png'
    Image.new('RGB', (120, 80), 'white').save(path)
    before = path.read_bytes()
    value = resized_image_input(path, 'TEST FIXTURE p1', 60)
    assert path.read_bytes() == before
    assert value.provenance['pixels'] == [60, 40]
    assert value.provenance['original_pixels'] == [120, 80]
    assert value.provenance['source_file_hash'] == sha256(before).hexdigest()
    assert value.provenance['file_hash'] != value.provenance['source_file_hash']
    for bad in (True, 0, -1, 120, 121, '60'):
        with pytest.raises(ValidationError): resized_image_input(path, 'TEST FIXTURE p1', bad)


def test_open_weight_common_record_roundtrip_and_phase_boundary(adopted, tmp_path):
    result = dict(model=MODEL_ID, revision=REVISION, status='output_limit', response_raw='TEST FIXTURE ONLY',
        run_id='test-only', timestamp='2026-10-01T00:00:00Z', prompt='人工例', visible_template='人工例',
        parameters={'max_new_tokens': 1}, elapsed_seconds=1, input_tokens=1, output_tokens=1)
    c,m = adopted
    context = material_context(c,m,'TRANSFER',for_input=False)
    r = reading_record(result, context, 'TEST FIXTURE p1')
    assert r['phase'] == 'transfer' and r['status'] == 'output_limit'
    assert r['cost_value'] is None and r['open_weight_result'] == result
    save_records([r],tmp_path/'record.md')
    assert load_records(tmp_path/'record.md') == [r]
    with pytest.raises(ValidationError):
        reading_record(result, material_context(c,m,'P0',for_input=False), 'TEST FIXTURE')
    changed = deepcopy(result);changed['model'] = 'other-model'
    with pytest.raises(ValueError): reading_record(changed,context,'TEST FIXTURE')


def test_model_save_uses_generation_context_and_one_annotation_for_all_formats(adopted, tmp_path):
    import json
    from seminar_lab.open_weight import save_result
    result = dict(model=MODEL_ID, revision=REVISION, status='output_limit', response_raw='TEST FIXTURE ONLY',
        run_id='test-only', timestamp='2026-10-01T00:00:00Z', prompt='人工例', visible_template='人工例',
        parameters={'max_new_tokens': 1}, elapsed_seconds=1, input_tokens=1, output_tokens=1,
        reading_context=material_context(*adopted, 'TRANSFER', for_input=False), source_location='TEST FIXTURE')
    original = deepcopy(result)
    annotations = {'student_explanation': '本人の説明', 'evidence_location': 'TEST FIXTURE', 'unresolved_point': '未確認'}
    saved, paths = save_result(result, annotations, tmp_path)
    assert result == original  # 返却値の代入前に以前の結果を書き換えない
    assert len(paths) == 3 and json.loads(paths[0].read_text()) == saved
    records = load_records(paths[1])
    assert load_records(paths[2]) == records
    assert records[0]['phase'] == 'transfer' and records[0]['material_id'] == 'P02'
    assert all(records[0][key] == value for key, value in annotations.items())
    assert records[0]['response_raw'] == 'TEST FIXTURE ONLY'
    before = {path: path.read_bytes() for path in paths}
    revised, later = save_result(saved, {'student_explanation': '改訂', 'unresolved_point': None}, tmp_path)
    assert all(path.read_bytes() == content for path, content in before.items())
    assert revised['unresolved_point'] == '未確認' and revised['student_explanation'] == '改訂'
    assert not set(paths) & set(later)

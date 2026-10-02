"""2報の教材と、朝・再読・Methods・別論文の記録境界。"""
from copy import deepcopy
from pathlib import Path
import pytest
from seminar_lab.config import check_course, material_context, ValidationError
from seminar_lab.records import new_record, save_records, load_records
from seminar_lab.ui import activity_view

ROOT = Path(__file__).resolve().parents[1]


def test_methods_and_transfer_are_separate_and_roundtrip(adopted, tmp_path):
    c, m = adopted
    before = deepcopy(c['common_reading'])
    contexts = [material_context(c, m, aid) for aid in ('P2a', 'METHODS', 'TRANSFER')]
    assert [(x['material_id'], x['phase'], x['question_set_id']) for x in contexts] == [
        ('P01', 'R2', 'Q_COMMON_3'), ('M01', None, 'Q_METHODS_5'), ('P02', 'transfer', 'Q_TRANSFER_3')]
    records = [new_record(x) for x in contexts]
    target = tmp_path / 'records.jsonl'
    save_records(records, target)
    assert load_records(target) == records
    assert c['common_reading'] == before
    for aid in ('METHODS', 'TRANSFER'):
        assert 'choices' not in activity_view(c, m, aid)
        with pytest.raises(ValidationError):
            material_context(c, m, aid, 'P01')
    records[-1]['phase'] = 'R3'
    with pytest.raises(ValidationError):
        save_records(records, tmp_path / 'invalid.jsonl')


@pytest.mark.parametrize('mutation', ['extra_paper', 'transfer_phase', 'transfer_choice', 'missing_methods', 'negative_minutes'])
def test_revision_contract_rejects_inconsistent_changes(adopted, mutation):
    c, m = adopted
    if mutation == 'extra_paper': c['day1_paper_ids'].append('E01')
    if mutation == 'transfer_phase': c['activities']['TRANSFER']['phase'] = 'R2'
    if mutation == 'transfer_choice': c['activities']['TRANSFER']['material_choice'] = True
    if mutation == 'missing_methods': c['question_sets']['Q_METHODS_5'].pop()
    if mutation == 'negative_minutes': c['activities']['L1']['segments_minutes'] = [13, -1]
    assert check_course(c, m, ROOT)


@pytest.mark.parametrize('activity,field,value', [('TRANSFER','phase',None),('TRANSFER','material_id','P01'),('METHODS','question_set_id','Q_COMMON_3')])
def test_record_loading_rejects_changed_activity_identity(adopted, tmp_path, activity, field, value):
    c,m=adopted
    r=new_record(material_context(c,m,activity,for_input=False))
    r[field]=value
    with pytest.raises(ValidationError):save_records([r],tmp_path/'bad.jsonl')

"""記録の破損を検知し、原文や過去の記録を黙って失わない。"""
import json
import pytest
from seminar_lab.config import ValidationError, material_context
from seminar_lab.records import load_records, new_record, save_records


@pytest.mark.parametrize('content', ['not json', '{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{"a": 1e999}'])
def test_invalid_json_has_explicit_error(tmp_path, content):
    path = tmp_path / 'record.jsonl'
    path.write_text(content)
    with pytest.raises(ValidationError):
        load_records(path)
    assert path.read_text() == content


@pytest.mark.parametrize('content', ['# 手書きのメモ', '<!-- SEMINAR_RECORDS -->\n```json\n[]', '<!-- SEMINAR_RECORDS -->\n```json\n{}\n```\n<!-- END_SEMINAR_RECORDS -->'])
def test_invalid_markdown_records_are_not_empty_success(tmp_path, content):
    path = tmp_path / 'record.md'
    path.write_text(content)
    with pytest.raises(ValidationError):
        load_records(path)


@pytest.mark.parametrize('suffix', ['.jsonl', '.md'])
def test_loading_duplicate_run_is_rejected(tmp_path, adopted, suffix):
    record = new_record(material_context(*adopted, 'P0'))
    path = tmp_path / ('record' + suffix)
    if suffix == '.jsonl':
        path.write_text((json.dumps(record) + '\n') * 2)
    else:
        path.write_text('<!-- SEMINAR_RECORDS -->\n```json\n' + json.dumps([record, record]) + '\n```\n<!-- END_SEMINAR_RECORDS -->')
    with pytest.raises(ValidationError, match='重複'):
        load_records(path)


@pytest.mark.parametrize('value', [-1, True, float('inf'), float('nan')])
def test_invalid_cost_does_not_create_file(tmp_path, adopted, value):
    record = new_record(material_context(*adopted, 'P0'))
    record.update(cost_kind='estimate', cost_value=value)
    path = tmp_path / 'record.jsonl'
    with pytest.raises(ValidationError):
        save_records([record], path)
    assert not path.exists()


def test_concatenated_markdown_does_not_discard_first_document(tmp_path, adopted):
    record = new_record(material_context(*adopted, 'P0'))
    path = tmp_path / 'record.md'
    save_records([record], path)
    combined = path.read_text() * 2
    path.write_text(combined)
    with pytest.raises(ValidationError, match='重複'):
        load_records(path)
    assert path.read_text() == combined


def test_student_text_with_machine_markers_roundtrips(tmp_path, adopted):
    record = new_record(material_context(*adopted, 'P0'))
    marker_text = '<!-- SEMINAR_RECORDS -->\n```json\n[]\n```\n<!-- END_SEMINAR_RECORDS -->'
    record.update(student_explanation=marker_text, evidence_location=marker_text)
    path = tmp_path / 'record.md'
    save_records([record], path)
    assert load_records(path) == [record]
    assert path.read_text().count('<!-- SEMINAR_RECORDS -->\n```json\n') == 1

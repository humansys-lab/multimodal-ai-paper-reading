"""Colabの選択画面だけを置換し、実Notebookセルの操作を検証する。"""
from pathlib import Path
from types import ModuleType, SimpleNamespace
from zipfile import ZipFile
import sys

import pytest
import yaml

from seminar_lab.ui import parse_pdf_pages, upload_one_file
from test_notebook_state import form_values
from test_standalone_workflows import book_namespace, action

BOOKS = ['01_dialogue_lab.ipynb']


def colab_files(monkeypatch, upload=None, download=None):
    """ブラウザとPythonの境界を再現。実Colabでの成功とは扱わない。"""
    module = ModuleType('google.colab')
    module.files = SimpleNamespace(upload=upload, download=download)
    monkeypatch.setitem(sys.modules, 'google.colab', module)
    return module.files


@pytest.mark.parametrize('text,expected', [('1-3', [1, 2, 3]), ('1,3', [1, 3]), ('2, 4-5', [2, 4, 5])])
def test_page_selection(text, expected):
    assert parse_pdf_pages(text) == expected


@pytest.mark.parametrize('text', ['', '0', '-1', '3-1', '1,1', '2,1', '1,,2', '1.5', 'a', '1-10000000'])
def test_bad_page_selection_stops(text):
    with pytest.raises(ValueError):
        parse_pdf_pages(text)


def test_upload_uses_saved_duplicate_filename(tmp_path, monkeypatch, capsys):
    directory = tmp_path / 'uploads'
    def upload(*, target_dir):
        assert Path(target_dir) == directory
        directory.mkdir()
        path = directory / 'connection.local (1).yaml'
        path.write_text('synthetic-secret-do-not-print')
        return {str(path): path.read_bytes()}
    colab_files(monkeypatch, upload=upload)
    path = upload_one_file(directory, {'.yaml'})
    assert path.name == 'connection.local (1).yaml'
    assert 'synthetic-secret' not in capsys.readouterr().out


@pytest.mark.parametrize('count', [0, 2])
def test_upload_cancel_or_multiple_stops(count, tmp_path, monkeypatch):
    colab_files(monkeypatch, upload=lambda **_: {f'{i}.yaml': b'' for i in range(count)})
    with pytest.raises(ValueError, match='1つだけ'):
        upload_one_file(tmp_path, {'.yaml'})


@pytest.mark.parametrize('filename', BOOKS)
def test_connection_upload_reuse_and_cancel(filename, tmp_path, monkeypatch, runtime):
    ns, nb = book_namespace(filename, tmp_path, monkeypatch)
    runtime.update(route='direct_openai', base_url='https://api.openai.com/v1', model='gpt-6-luna')
    calls = []
    def upload(*, target_dir):
        calls.append(target_dir)
        p = Path(target_dir) / 'connection.local (1).yaml'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump({'runtime': runtime}))
        return {str(p): p.read_bytes()}
    boundary = colab_files(monkeypatch, upload=upload)
    connection = action(nb, 'connection_path =')
    exec(form_values(connection, UPLOAD_CONNECTION=True), ns)
    assert ns['runtime']['model'] == 'gpt-6-luna'
    session = ns['session']
    exec(form_values(connection, model='gpt-4.1-mini'), ns)
    assert ns['runtime']['model'] == 'gpt-4.1-mini' and len(calls) == 1
    assert ns['session'] is session
    boundary.upload = lambda **_: {}
    with pytest.raises(ValueError, match='1つだけ'):
        exec(form_values(connection, UPLOAD_CONNECTION=True), ns)
    assert ns['runtime'] is None and ns['connection_file'] is None


@pytest.mark.parametrize('filename', BOOKS)
def test_question_prepares_next_run_without_counter_cell(filename, tmp_path, monkeypatch, runtime):
    ns, nb = book_namespace(filename, tmp_path, monkeypatch)
    ns.update(runtime=runtime, model=runtime['model'], activity_id='PRACTICE')
    question = action(nb, 'previewed_request = None')
    exec(form_values(question, question='最初の質問', max_output_tokens=100), ns)
    first_id = ns['run_id']
    assert ns['previewed_request'] and not ns['session'].records
    exec(form_values(question, question='次の質問', max_output_tokens=100), ns)
    assert ns['run_id'] != first_id
    assert ns['previewed_request'][1]['input'][-1]['content'][-1]['text'] == '次の質問'
    assert not any('START_NEXT_RUN' in ''.join(c['source']) for c in nb['cells'])
    second_id = ns['run_id']
    exec(question, ns)  # 空欄にした場合、以前のプレビューを送らない。
    assert ns['previewed_request'] is None and ns['run_id'] != second_id


@pytest.mark.parametrize('filename', BOOKS)
def test_save_forms_and_download_keep_raw_response(filename, tmp_path, monkeypatch):
    ns, nb = book_namespace(filename, tmp_path, monkeypatch)
    # 記録の骨格を実際の関数で作る。APIは呼ばない。
    context = ns['material_context'](ns['course'], ns['manifest'], 'PRACTICE')
    record = ns['new_record'](session_id='synthetic', context=context)
    record['response_raw'] = {'artificial': 'TEST FIXTURE ONLY'}
    record['student_explanation'] = '前の記入'
    ns.update(session=SimpleNamespace(records=[record]), result=record, run_id=record['run_id'])
    downloads = []
    colab_files(monkeypatch, download=lambda path: downloads.append(Path(path)))
    save = action(nb, 'annotations =')
    exec(form_values(save, SAVE=True, DOWNLOAD=True, student_explanation='自分の説明', evidence_location='人工図'), ns)
    assert record['student_explanation'] == '自分の説明'
    assert record['response_raw'] == {'artificial': 'TEST FIXTURE ONLY'}
    with ZipFile(downloads[0]) as z:
        assert set(z.namelist()) == {p.name for p in ns['paths']}
        for p in ns['paths']:
            assert z.read(p.name) == p.read_bytes()
    first = downloads[0].read_bytes()
    exec(form_values(save, SAVE=True), ns)  # 空欄の再保存で説明を消さない。
    assert record['student_explanation'] == '自分の説明'
    assert downloads[0].read_bytes() == first


def test_multiline_question_and_excerpt_survive_actual_cells(tmp_path, monkeypatch, runtime):
    ns, nb = book_namespace('01_dialogue_lab.ipynb', tmp_path, monkeypatch)
    ns.update(runtime=runtime, model=runtime['model'], activity_id='PRACTICE')
    question = 'What differs?\nPlease give the evidence.'
    excerpt = 'The value of A was 2.\nThe value of B was 5.'
    entry = action(nb, 'source_excerpt =')
    assert '# @param' not in entry
    exec(form_values(entry, question=question, source_excerpt=excerpt, source_location='人工資料'), ns)
    confirm = next(''.join(c['source']) for c in nb['cells'] if c.get('id') == 'cell-09')
    exec(form_values(confirm, max_output_tokens=100), ns)
    payload = ns['previewed_request'][1]
    text_parts = [part['text'] for message in payload['input'] for part in message['content'] if 'text' in part]
    assert question in text_parts and excerpt in text_parts

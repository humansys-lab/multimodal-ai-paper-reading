"""簡潔な02の実セルをSDKのHTTP境界で検査する。人工応答は実測と扱わない。"""
import base64
from copy import deepcopy
import io
import json
from pathlib import Path
from types import ModuleType
import sys

import httpx
from openai import OpenAI
from PIL import Image
from pypdf import PdfWriter
import pytest

from test_notebook_state import form_values
from test_standalone_workflows import book_namespace

ROOT = Path(__file__).resolve().parents[1]
NAME = '02_document_lab.ipynb'


def cell(nb, id):
    return next(''.join(c['source']) for c in nb['cells'] if c['id'] == id)


def answer(model, status='completed'):
    return {'id': 'test', 'created_at': 0, 'object': 'response', 'model': model,
            'status': status, 'output': [{'id': 'msg', 'type': 'message', 'role': 'assistant',
            'status': status, 'content': [{'type': 'output_text', 'text': '人工応答', 'annotations': []}]}],
            'usage': {'input_tokens': 8, 'output_tokens': 3, 'total_tokens': 11},
            'incomplete_details': {'reason': 'max_output_tokens'} if status == 'incomplete' else None}


def runtime(tmp_path, monkeypatch, model='gpt-6-luna', outcome='completed'):
    ns, nb = book_namespace(NAME, tmp_path, monkeypatch)
    calls = []
    def handler(request):
        payload = json.loads(request.content)
        calls.append(deepcopy(payload))
        if isinstance(outcome, int):
            return httpx.Response(outcome, json={'error': {'message': 'secret-error-body', 'type': 'test'}})
        if outcome == 'timeout':
            raise httpx.ReadTimeout('secret-error-body', request=request)
        return httpx.Response(200, json=answer(payload['model'], outcome))
    def factory(**kwargs):
        assert kwargs['max_retries'] == 0
        assert kwargs['base_url'] == 'https://api.openai.com/v1'
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr('openai.OpenAI', factory)
    monkeypatch.setattr('getpass.getpass', lambda *_: 'synthetic-test-key')
    exec(form_values(cell(nb, 'connect'), CONNECT=True, model=model), ns)
    assert not calls and 'api_key' not in ns
    return ns, nb, calls


def fixture_data(kind):
    output = io.BytesIO()
    if kind == 'pdf':
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=200, height=200)
        writer.write(output)
    else:
        Image.new('RGB', (20, 10), 'blue').save(output, format=kind.upper())
    return output.getvalue()


def upload(ns, nb, tmp_path, kind, data=None):
    data = fixture_data(kind) if data is None else data
    path = tmp_path / ('test.' + kind)
    path.write_bytes(data)
    exec(form_values(cell(nb, 'upload'), UPLOAD=True, local_path=str(path)), ns)
    return data


@pytest.mark.parametrize('model', ['gpt-6-luna', 'gpt-6-sol', 'gpt-4.1-mini'])
@pytest.mark.parametrize('kind', ['text', 'png', 'jpeg', 'pdf'])
def test_sdk_receives_exact_question_and_file_without_history(model, kind, tmp_path, monkeypatch):
    ns, nb, calls = runtime(tmp_path, monkeypatch, model)
    data = None if kind == 'text' else upload(ns, nb, tmp_path, kind)
    source = cell(nb, 'text-question' if kind == 'text' else 'file-question')
    for question in ['日本語の質問\n2行目', '次の質問']:
        exec(form_values(source, SEND=True, question=question), ns)
        payload = calls[-1]
        assert payload['model'] == model and payload['store'] is False
        assert payload['max_output_tokens'] == 2048
        assert payload.get('reasoning', {}).get('effort') == {'gpt-6-luna': 'none', 'gpt-6-sol': 'low', 'gpt-4.1-mini': None}[model]
        assert not any(key in payload for key in ['previous_response_id', 'conversation', 'tools', 'instructions'])
        if kind == 'text':
            assert payload['input'] == question
        else:
            assert len(payload['input']) == 1
            content = payload['input'][0]['content']
            assert content[1] == {'type': 'input_text', 'text': question}
            attachment = content[0]
            field = 'file_data' if kind == 'pdf' else 'image_url'
            assert base64.b64decode(attachment[field].split(',', 1)[1]) == data
        assert ns['response'].status == 'completed'
    assert len(calls) == 2
    assert not (tmp_path / 'outputs').exists()
    assert not any(key in ns for key in ['session', 'activity', 'activity_id', 'course', 'manifest'])
    ns['client'].close()


@pytest.mark.parametrize('kind', ['text-question', 'file-question'])
@pytest.mark.parametrize('outcome', ['incomplete', 401, 403, 429, 500, 'timeout'])
def test_failure_is_visible_and_never_retried(kind, outcome, tmp_path, monkeypatch, capsys):
    ns, nb, calls = runtime(tmp_path, monkeypatch, outcome=outcome)
    if kind == 'file-question':upload(ns, nb, tmp_path, 'png')
    ns['response'] = 'previous answer'
    source = form_values(cell(nb, kind), SEND=True, question='人工質問')
    if outcome == 'incomplete':
        exec(source, ns)
        assert ns['response'].status == 'incomplete'
        assert 'max_output_tokens' in capsys.readouterr().out
    else:
        with pytest.raises(RuntimeError, match='API送信に失敗') as error:exec(source, ns)
        assert ns['response'] is None
        assert 'secret-error-body' not in str(error.value)
        assert 'synthetic-test-key' not in str(error.value)
    assert len(calls) == 1
    ns['client'].close()


@pytest.mark.parametrize('case', ['empty', 'missing_file', 'bad_file', 'cancel', 'multiple'])
def test_input_failure_never_sends_old_input(case, tmp_path, monkeypatch):
    ns, nb, calls = runtime(tmp_path, monkeypatch)
    upload(ns, nb, tmp_path, 'png')
    if case == 'empty':
        with pytest.raises(ValueError, match='質問'):exec(form_values(cell(nb, 'file-question'), SEND=True), ns)
    elif case == 'missing_file':
        with pytest.raises(FileNotFoundError):
            exec(form_values(cell(nb, 'upload'), UPLOAD=True, local_path=str(tmp_path/'missing.png')), ns)
        assert ns['attachment'] is None
    elif case == 'bad_file':
        with pytest.raises(ValueError, match='中身'):upload(ns, nb, tmp_path, 'png', b'not a png')
        assert ns['attachment'] is None
    else:
        colab = ModuleType('google.colab')
        colab.files = type('Files', (), {'upload': staticmethod(lambda **_: {} if case == 'cancel' else {'a.png': b'a', 'b.png': b'b'})})
        monkeypatch.setitem(sys.modules, 'google.colab', colab)
        with pytest.raises(ValueError, match='1つだけ'):exec(form_values(cell(nb, 'upload'), UPLOAD=True), ns)
        assert ns['attachment'] is None
    assert calls == []
    ns['client'].close()


def test_colab_upload_uses_bytes_returned_with_renamed_file(tmp_path, monkeypatch):
    ns, nb, calls = runtime(tmp_path, monkeypatch)
    data = fixture_data('png')
    colab = ModuleType('google.colab')
    def chooser(*, target_dir):
        assert Path(target_dir) == tmp_path / 'private/uploads'
        return {str(Path(target_dir) / 'figure (1).png'): data}
    colab.files = type('Files', (), {'upload': staticmethod(chooser)})
    monkeypatch.setitem(sys.modules, 'google.colab', colab)
    exec(form_values(cell(nb, 'upload'), UPLOAD=True), ns)
    assert ns['filename'] == 'figure (1).png'
    assert base64.b64decode(ns['attachment']['image_url'].split(',',1)[1]) == data
    assert not calls
    ns['client'].close()


@pytest.mark.parametrize('model', ['gpt-6-astra', 'GPT-6-LUNA', 'gpt-6.1-sol'])
def test_non_classroom_model_rejected(model, tmp_path, monkeypatch):
    ns, nb = book_namespace(NAME, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='3モデル'):exec(form_values(cell(nb, 'connect'), model=model), ns)


def test_no_record_setup_or_extra_installs(tmp_path, monkeypatch):
    ns, nb = book_namespace(NAME, tmp_path, monkeypatch)
    source = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
    assert len([c for c in nb['cells'] if c['cell_type']=='code']) == 5
    assert 'openai==2.54.0' in cell(nb,'install')
    assert not any(s in source for s in ['import yaml', 'import pypdf', 'from PIL', 'Session(', 'material_context(', 'SAVE =', 'activity_id', 'permission'])
    assert ns['response'] is None and ns['client'] is None and ns['attachment'] is None
    assert list(tmp_path.iterdir()) == []

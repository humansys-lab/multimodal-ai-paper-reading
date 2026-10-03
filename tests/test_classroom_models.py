"""採用3モデルの実セル・設定・エラーを通信なしで検証する。"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest
import yaml

from seminar_lab.client import OpenAITransport, Session, TransportError, validate_response
from seminar_lab.config import COURSE_MODELS, ValidationError, validate_runtime
from seminar_lab.connection import load_runtime, select_model

ROOT = Path(__file__).resolve().parents[1]


def direct(runtime):
    runtime = deepcopy(runtime)
    runtime.update(route='direct_openai', base_url='https://api.openai.com/v1')
    return runtime


@pytest.mark.parametrize('model', list(COURSE_MODELS))
@pytest.mark.parametrize('name', ['01_dialogue_lab.ipynb', '02_document_lab.ipynb'])
def test_notebook_model_picker_and_question_cells(name, model, runtime, tmp_path):
    """self-containedの実セルから、選択モデルに合う送信内容を構築する。"""
    n = json.loads((ROOT / 'notebooks' / name).read_text())
    ns = {}
    for c in n['cells']:
        if c['cell_type'] == 'code' and c['metadata'].get('embedded_support'):
            exec(''.join(c['source']), ns)
    def cell(marker):
        return next(''.join(c['source']) for c in n['cells']
                    if c['cell_type'] == 'code' and not c['metadata'].get('embedded_support')
                    and marker in ''.join(c['source']))
    p = tmp_path / 'connection.yaml'
    p.write_text(yaml.safe_dump({'runtime': direct(runtime)}))
    code = cell('connection_path =').replace("connection_path = ''", f'connection_path = {str(p)!r}')
    code = code.replace("model = 'gpt-6-luna'", f'model = {model!r}')
    exec(code, ns)
    session = ns['session']
    ns['question'] = ns['source_excerpt'] = ns['source_location'] = ''
    exec(cell('max_output_tokens ='), ns)
    payload = session.preview(ns['runtime'], '人工質問', [], 'new', ns['parameters'])
    assert payload['model'] == model and payload['max_output_tokens'] == 2048
    assert payload['store'] is False and payload['truncation'] == 'disabled'
    expected = {'gpt-6-luna': 'none', 'gpt-6-sol': 'low', 'gpt-4.1-mini': None}[model]
    assert payload.get('reasoning', {}).get('effort') == expected
    assert ('include' in payload) == model.startswith('gpt-6')
    assert not session.records
    exec(code, ns)
    assert ns['session'] is session


@pytest.mark.parametrize('model', ['gpt-6-astra', 'gpt-6.1-sol', 'GPT-6-SOL', 'GPT-6-LUNA', 'GPT-4.1-MINI', 'gpt-4.1', 'gpt-4.1-mini-malicious', ''])
def test_unselected_models_rejected(model, runtime):
    with pytest.raises(ValidationError, match='モデルは'):
        select_model(direct(runtime), model)


@pytest.mark.parametrize('model,params,valid', [
    ('gpt-6-luna', {'reasoning': {'effort': 'none'}, 'temperature': 0.7}, True),
    ('gpt-6-luna', {'reasoning': {'effort': 'low'}, 'temperature': 0.7}, False),
    ('gpt-6-luna', {'top_p': 0.5}, False),
    ('gpt-6-luna', {'reasoning': {'effort': 'low'}}, True),
    ('gpt-6-sol', {'reasoning': {'effort': 'none'}}, True),
    ('gpt-6-sol', {'reasoning': {'effort': 'none'}, 'temperature': 0.7}, True),
    ('gpt-6-sol', {'reasoning': {'effort': 'low'}, 'temperature': 0.7}, False),
    ('gpt-6-sol', {'reasoning': {'effort': 'low', 'mode': 'pro'}}, False),
    ('gpt-6-sol', {'reasoning': {'effort': 'high'}}, True),
    ('gpt-4.1-mini', {'reasoning': {'effort': 'none'}}, False),
    ('gpt-4.1-mini', {'temperature': 0.7}, True),
    ('gpt-4.1-mini', {'top_p': 0.9}, True),
])
def test_settings_are_not_silently_dropped(model, params, valid, runtime):
    r = select_model(direct(runtime), model)
    values = {'max_output_tokens': 4096, **params}
    before = deepcopy(values)
    if valid:
        validate_runtime(r, {'text', 'image', 'pdf'}, values)
    else:
        with pytest.raises(ValidationError):
            validate_runtime(r, {'text'}, values)
    assert values == before


def test_alias_matches_only_its_observed_snapshot():
    raw = {'model': 'gpt-4.1-mini-2025-04-14', 'output': [
        {'type': 'message', 'role': 'assistant', 'status': 'completed',
         'content': [{'type': 'output_text', 'text': '人工応答'}]}]}
    validate_response(raw, 'gpt-4.1-mini')
    for other in ['gpt-4.1-2025-04-14', 'gpt-4.1-mini-2099-01-01', 'gpt-6-astra']:
        with pytest.raises(TransportError, match='モデル'):
            validate_response({**raw, 'model': other}, 'gpt-4.1-mini')


def test_model_switch_requires_new_conversation(runtime):
    a = select_model(direct(runtime), 'gpt-4.1-mini')
    b = select_model(direct(runtime), 'gpt-6-sol')
    s = Session()
    s._history = [{'role': 'user', 'content': '人工履歴'}]
    s._runtime = a
    before = s.history
    with pytest.raises(ValidationError, match='新規会話'):
        s.preview(b, '質問', [], 'continue', {'max_output_tokens': 2048})
    assert s.preview(b, '質問', [], 'new', {'max_output_tokens': 2048})['model'] == 'gpt-6-sol'
    assert s.history == before


def test_proxy_capabilities_not_inferred_from_direct_api(runtime):
    with pytest.raises(ValidationError, match='中継'):
        select_model(runtime, 'gpt-6-sol')


def test_access_error_is_clear_and_not_retried(runtime, monkeypatch):
    calls = []
    def denied(**payload):
        calls.append(payload)
        response = httpx.Response(403, request=httpx.Request('POST', 'https://api.openai.com/v1/responses'))
        raise openai.PermissionDeniedError('private message', response=response, body={'code': 'model_not_found'})
    def client(**kwargs):
        assert kwargs['max_retries'] == 0
        return SimpleNamespace(responses=SimpleNamespace(create=denied), close=kwargs['http_client'].close)
    monkeypatch.setattr(openai, 'OpenAI', client)
    monkeypatch.setattr('seminar_lab.client.version', lambda _: runtime['sdk_version'])
    r = select_model(direct(runtime), 'gpt-6-luna')
    t = OpenAITransport(r, 'synthetic-key')
    try:
        with pytest.raises(TransportError) as error:
            t.send({'model': 'gpt-6-luna'})
    finally:
        t.close()
    assert error.value.kind == 'model_access' and len(calls) == 1
    assert 'private message' not in str(error.value) and 'synthetic-key' not in str(error.value)

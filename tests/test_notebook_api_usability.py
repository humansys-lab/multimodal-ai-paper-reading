"""授業の実セルを使い、許可照合なしの再読込み・再定義・送信を検査する。"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
from PIL import Image
import pytest
import yaml

from seminar_lab.config import ValidationError, validate_runtime
from seminar_lab.connection import load_runtime

ROOT = Path(__file__).resolve().parents[1]


def test_old_connection_does_not_limit_classroom_requests(tmp_path, runtime):
    """旧512固定と変更された許可情報を、授業内の送信制限として使わない。"""
    runtime['capabilities']['parameters']['max_output_tokens'] = {'min': 512, 'max': 512}
    config = {'runtime': runtime, 'permission': {'id': 'old', 'request_limit': 0}}
    path = tmp_path / 'connection.yaml'
    path.write_text(yaml.safe_dump(config))
    for limit in (128, 2048, 4096):
        loaded = load_runtime(path)
        validate_runtime(loaded, {'pdf'}, {'max_output_tokens': limit})
    config['permission'] = {'id': 'old', 'request_limit': 100, 'approved_by': 'changed'}
    path.write_text(yaml.safe_dump(config))
    assert load_runtime(path) == loaded
    for limit in (0, -1, True, '2048'):
        with pytest.raises(ValidationError):
            validate_runtime(loaded, {'pdf'}, {'max_output_tokens': limit})


@pytest.mark.parametrize('name', ['01_dialogue_lab.ipynb', '02_document_lab.ipynb'])
@pytest.mark.parametrize('outcome', ['completed', 'incomplete', 'budget'])
def test_actual_cells_reload_and_send_without_permission(name, outcome, tmp_path, runtime, monkeypatch):
    """API境界だけ人工応答。準備セル再定義後も記録と継続履歴を保持する。"""
    notebook = json.loads((ROOT / 'notebooks' / name).read_text())
    support = [''.join(c['source']) for c in notebook['cells']
               if c['cell_type'] == 'code' and c['metadata'].get('embedded_support')]
    assert not any('class LivePermission:' in s or 'def load_connection(' in s for s in support)
    def cell(marker):
        matches = [''.join(c['source']) for c in notebook['cells']
                   if c['cell_type'] == 'code' and not c['metadata'].get('embedded_support')
                   and marker in ''.join(c['source'])]
        assert len(matches) == 1
        return matches[0]

    config_path = tmp_path / 'connection.yaml'
    runtime.update(route='direct_openai', base_url='https://api.openai.com/v1', model='gpt-4.1-mini')
    config_path.write_text(yaml.safe_dump({'runtime': runtime}))
    config_cell = cell('connection_path =').replace("connection_path = ''", f'connection_path = {str(config_path)!r}')
    config_cell = config_cell.replace("model = 'gpt-6-luna'", "model = 'gpt-4.1-mini'")
    calls, clients = [], []
    replies = ['completed', outcome]

    class ArtificialClient:
        def __init__(self, **kwargs):
            self.http = kwargs['http_client']
            self.closed = False
            self.responses = self
            clients.append(self)
            assert kwargs['max_retries'] == 0

        def create(self, **payload):
            calls.append(deepcopy(payload))
            status = replies.pop(0)
            if status == 'budget':
                response = httpx.Response(429, request=httpx.Request('POST', 'https://example.invalid'))
                raise openai.APIStatusError('private error must not leak', response=response,
                                            body={'code': 'insufficient_quota'})
            raw = {'status': status, 'model': payload['model'], 'usage': {'output_tokens': 5},
                   'output': [{'type': 'message', 'role': 'assistant', 'status': status,
                               'content': [{'type': 'output_text', 'text': '人工応答：試験用'}]}]}
            if status == 'incomplete':
                raw['incomplete_details'] = {'reason': 'max_output_tokens'}
            return SimpleNamespace(model_dump=lambda **_: raw)

        def close(self):
            self.http.close()
            self.closed = True

    monkeypatch.setattr(openai, 'OpenAI', ArtificialClient)
    monkeypatch.setattr('getpass.getpass', lambda *_: 'artificial-test-key')
    ns = {}
    for s in support:
        exec(s, ns)
    ns['version'] = lambda _: runtime['sdk_version']
    exec(config_cell, ns)
    session = ns['session']
    ns.update(question='人工資料についての質問', parameters={'max_output_tokens': 2048},
              conversation_mode='new', inputs=[])
    if name.startswith('02'):
        image_path = tmp_path / 'synthetic.png'
        Image.new('RGB', (8, 8), 'white').save(image_path)
        ns['inputs'] = [ns['image_input'](image_path, '試験用の人工画像')]
    exec(cell('previewed_request = None'), ns)
    exec(cell('SEND =').replace('SEND = False', 'SEND = True'), ns)
    assert ns['result']['status'] == 'success'
    first_history = deepcopy(session.history)

    # 再定義でクラスの同一性は変わる。既存セッションはそのまま継続する。
    for s in support:
        exec(s, ns)
    ns['version'] = lambda _: runtime['sdk_version']
    changed = deepcopy(runtime)
    changed['timeout_seconds'] = 45
    config_path.write_text(yaml.safe_dump({'runtime': changed, 'permission': {'id': 'old', 'request_limit': 0}}))
    exec(config_cell, ns)
    assert ns['session'] is session and session.history == first_history
    assert 'permissions' not in ns and 'permission' not in ns
    ns.update(question='続きの人工質問', conversation_mode='continue', parameters={'max_output_tokens': 4096})
    exec(cell('START_NEXT_RUN =').replace('START_NEXT_RUN = False', 'START_NEXT_RUN = True'), ns)
    exec(cell('previewed_request = None'), ns)
    exec(cell('SEND =').replace('SEND = False', 'SEND = True'), ns)
    assert len(calls) == 2 and all(c.closed for c in clients)
    assert calls[1]['max_output_tokens'] == 4096
    assert calls[1]['input'][:len(first_history)] == first_history
    assert len(session.records) == 2
    expected = {'completed': 'success', 'incomplete': 'incomplete', 'budget': 'failed'}[outcome]
    assert ns['result']['status'] == expected
    if outcome != 'completed':
        assert session.history == first_history
    if outcome == 'budget':
        assert ns['result']['error_type'] == 'budget'
    assert 'private error must not leak' not in str(session.records)
    assert 'artificial-test-key' not in str(session.records)

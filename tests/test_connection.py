"""学生の接続ファイルを実際に読み、許可枠・モデル・秘密入力の境界を確認する。"""
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from seminar_lab.connection import load_connection
from seminar_lab.config import ValidationError


@pytest.fixture
def connection(runtime):
    runtime['capabilities']['parameters']['max_output_tokens']['max'] = 1024
    return {'runtime': runtime, 'permission': {
        'id': 'synthetic-permission', 'approved_by': 'test fixture', 'scope': 'synthetic tests',
        'route': runtime['route'], 'model': runtime['model'], 'authentication_route': 'test fixture',
        'usd_limit': 1, 'request_limit': 2,
    }}


def write_config(tmp_path, config):
    path = tmp_path / 'connection.yaml'
    path.write_text(yaml.safe_dump(config))
    return path


def test_reading_connection_preserves_consumed_requests(tmp_path, connection):
    path = write_config(tmp_path, connection)
    cache = {}
    runtime, permission = load_connection(path, cache)
    permission.consume(runtime)
    runtime_again, permission_again = load_connection(path, cache)
    assert runtime_again == runtime and permission_again is permission
    assert permission_again.used == 1
    permission.consume(runtime)
    with pytest.raises(ValidationError, match='呼出し枠'):
        load_connection(path, cache)
    assert permission.used == 2


def test_changed_permission_id_cannot_reset_same_grant(tmp_path, connection):
    path = write_config(tmp_path, connection)
    cache = {}
    runtime, permission = load_connection(path, cache)
    permission.consume(runtime)
    changed = deepcopy(connection)
    changed['permission']['request_limit'] = 20
    write_config(tmp_path, changed)
    with pytest.raises(ValidationError, match='変更'):
        load_connection(path, cache)
    assert permission.used == 1 and permission.request_limit == 2


def test_two_teacher_model_configs_keep_independent_counters(tmp_path, connection):
    cache = {}
    runtime1, p1 = load_connection(write_config(tmp_path, connection), cache)
    p1.consume(runtime1)
    other = deepcopy(connection)
    other['permission']['id'] = 'second-teacher-permission'
    other['runtime']['model'] = other['permission']['model'] = 'second-fixture-model'
    runtime2, p2 = load_connection(write_config(tmp_path, other), cache)
    p2.consume(runtime2)
    assert p1 is not p2 and p1.used == p2.used == 1
    assert load_connection(write_config(tmp_path, connection), cache)[1] is p1


@pytest.mark.parametrize('where,name,value', [
    ('permission', 'used', 0), ('permission', 'request_limit', True),
    ('permission', 'id', ''), ('permission', 'model', 'wrong-model'),
    ('permission', 'api_key', 'do-not-display-this-secret'),
    ('runtime', 'api_key', 'do-not-display-this-secret'),
])
def test_invalid_or_secret_configuration_never_enters_cache(tmp_path, connection, where, name, value):
    connection[where][name] = value
    cache = {}
    with pytest.raises(ValidationError) as error:
        load_connection(write_config(tmp_path, connection), cache)
    assert not cache and 'do-not-display-this-secret' not in str(error.value)


def test_public_example_is_not_permission_to_send():
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(ValidationError):
        load_connection(root / 'config/connection.example.yaml', {})

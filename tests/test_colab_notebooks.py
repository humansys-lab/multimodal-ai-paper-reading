"""各Notebookを単独配布できることと、埋込み処理の追跡可能性。"""
from pathlib import Path
import ast
import json
import os
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
BOOKS = sorted(p.name for p in (ROOT / 'notebooks').glob('0*.ipynb'))


@pytest.mark.parametrize('filename', BOOKS)
def test_notebook_runs_alone_without_repository(filename, tmp_path):
    """ipynbだけを空フォルダへコピー。repo importと通信を禁止して全既定セルを実行。"""
    target = tmp_path / filename
    target.write_bytes((ROOT / 'notebooks' / filename).read_bytes())
    script = '''import builtins, json, pathlib, socket
original_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith('seminar_lab'):
        raise AssertionError('repository import forbidden')
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded
def blocked(*args, **kwargs):
    raise AssertionError('network forbidden')
socket.socket.connect = blocked
for cell in json.loads(pathlib.Path(%r).read_text())['cells']:
    if cell['cell_type'] == 'code':
        exec(compile(''.join(cell['source']), 'isolated notebook cell', 'exec'), globals())
print('standalone pass')
''' % filename
    # 00はsite-packagesも使わない。ほかの冊子は環境に導入済みの通常ライブラリを使う。
    command = [sys.executable, '-I'] + (['-S'] if filename.startswith('00') else []) + ['-c', script]
    completed = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert 'standalone pass' in completed.stdout
    assert not (tmp_path / 'src').exists() and not (tmp_path / 'config').exists()


def test_embedded_support_matches_verified_source():
    sys.path.insert(0, str(ROOT / 'scripts'))
    from embed_notebook_support import refresh
    assert all(not refresh(ROOT / 'notebooks' / name, check=True) for name in BOOKS)


@pytest.mark.parametrize('filename', BOOKS)
def test_no_hidden_code_download_or_import(filename):
    nb = json.loads((ROOT / 'notebooks' / filename).read_text())
    code = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code')
    tree = ast.parse(code)
    assert not any(isinstance(n, ast.ImportFrom) and ((n.module or '').startswith('seminar_lab') or n.level) for n in ast.walk(tree))
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'exec', 'eval', '__import__'} for n in ast.walk(tree))
    for hidden in ('RELEASE_COMMIT', 'urlopen', 'sys.path.insert', "ROOT / 'config/", "ROOT / 'requirements-"):
        assert hidden not in code
    assert any(c.get('id') == 'input-output-examples' for c in nb['cells'])


def test_only_required_external_libraries():
    code = lambda name: '\n'.join(''.join(c['source']) for c in json.loads((ROOT/'notebooks'/name).read_text())['cells'] if c['cell_type']=='code')
    assert 'import yaml' not in code('00_setup.ipynb')
    assert 'import yaml' not in code('03_open_weight_lab.ipynb')
    first = next(c for c in json.loads((ROOT/'notebooks/01_dialogue_lab.ipynb').read_text())['cells'] if c['cell_type']=='code')
    assert "packages = ['openai==2.54.0', 'pyyaml==6.0.3']" in ''.join(first['source'])

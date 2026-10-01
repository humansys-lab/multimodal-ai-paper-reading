"""短い取得セルの固定版と、取得後に実行するコードの検証境界。"""
from hashlib import sha256
from pathlib import Path
import json
import re
from io import BytesIO
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_every_notebook_pins_same_archive_and_bootstrap():
    digest = sha256((ROOT / 'scripts/colab_bootstrap.py').read_bytes()).hexdigest()
    pins = set()
    for path in (ROOT / 'notebooks').glob('0*.ipynb'):
        nb = json.loads(path.read_text())
        cell = ''.join(nb['cells'][1]['source'])
        assert f'BOOTSTRAP_SHA256 = "{digest}"' in cell
        assert len(cell.splitlines()) <= 32
        commit = re.search(r'^RELEASE_COMMIT = (.+)$', cell, re.M).group(1).split(' #')[0]
        archive = re.search(r'^RELEASE_SHA256 = (.+)$', cell, re.M).group(1)
        assert re.fullmatch(r'"[0-9a-f]{40}"', commit)
        assert re.fullmatch(r'"[0-9a-f]{64}"', archive)
        pins.add((commit, archive))
        assert 'PREPARE_COLAB = False' in cell
    assert len(pins) == 1


def test_changed_download_never_executes():
    nb = json.loads((ROOT / 'notebooks/01_dialogue_lab.ipynb').read_text())
    cell = ''.join(nb['cells'][1]['source'])
    cell = cell.replace('PREPARE_COLAB = False', 'PREPARE_COLAB = True')
    cell = re.sub(r'^RELEASE_COMMIT = .+$', 'RELEASE_COMMIT = "' + 'a'*40 + '"', cell, flags=re.M)
    cell = re.sub(r'^RELEASE_SHA256 = .+$', 'RELEASE_SHA256 = "' + 'b'*64 + '"', cell, flags=re.M)
    with patch('urllib.request.urlopen', return_value=BytesIO(b'raise AssertionError("must not execute")')):
        with pytest.raises(RuntimeError, match='ハッシュ'):
            exec(cell, {})

"""Notebookに埋め込んだ取得処理が検査済みの正本と一致することを確認する。"""
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def test_every_notebook_pins_same_archive_and_bootstrap():
    source = (ROOT / 'scripts/colab_bootstrap.py').read_text().strip()
    pins = set()
    for path in (ROOT / 'notebooks').glob('0*.ipynb'):
        nb = json.loads(path.read_text())
        cell = ''.join(nb['cells'][1]['source'])
        embedded = cell.split('# BEGIN VERIFIED BOOTSTRAP\n', 1)[1].split('# END VERIFIED BOOTSTRAP', 1)[0].strip()
        assert sha256(embedded.encode()).digest() == sha256(source.encode()).digest()
        commit = re.search(r'RELEASE_COMMIT = "([0-9a-f]{40})"', cell).group(1)
        digest = re.search(r'RELEASE_SHA256 = "([0-9a-f]{64})"', cell).group(1)
        pins.add((commit, digest))
        assert 'PREPARE_COLAB = False' in cell
    assert len(pins) == 1

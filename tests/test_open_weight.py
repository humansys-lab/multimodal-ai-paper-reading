"""外部取得・推論を伴わず、誤送信と暗黙の切替を防ぐ検査。"""
import os
from pathlib import Path
import pytest
from seminar_lab.open_weight import configure_cache, load_model, generate


def test_cache_cannot_escape_through_symlink(tmp_path, monkeypatch):
    root = tmp_path / 'course'; root.mkdir()
    external = tmp_path / 'external'; external.mkdir()
    (root / 'build').symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match='教材フォルダ内'):
        configure_cache(root)
    assert not (external / 'open-weight-cache').exists()


def test_device_and_output_limit_rejected_before_import(monkeypatch):
    with pytest.raises(ValueError, match='device'):
        load_model('auto')
    monkeypatch.setenv('PYTORCH_ENABLE_MPS_FALLBACK', '1')
    with pytest.raises(ValueError, match='フォールバック'):
        load_model('mps')
    with pytest.raises(ValueError, match='出力上限'):
        generate(None, None, 'test', max_new_tokens=129)

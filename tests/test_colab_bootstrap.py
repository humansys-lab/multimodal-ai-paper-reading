"""公開アーカイブの展開境界。ネットワーク・Colab実機の代わりにはしない。"""
from pathlib import Path
from io import BytesIO
import importlib.util
import stat
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('colab_bootstrap', ROOT / 'scripts/colab_bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
COMMIT = 'a' * 40
PREFIX = 'multimodal-ai-paper-reading-' + COMMIT


def archive(extra=None):
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        for name in ['src/seminar_lab/__init__.py', 'config/course.yaml', 'materials/manifest.yaml', 'requirements-colab.txt']:
            z.writestr(PREFIX + '/' + name, 'test fixture only')
        if extra is not None:
            if extra == PREFIX + '/config/course.yaml':
                with pytest.warns(UserWarning, match='Duplicate name'):
                    z.writestr(extra, 'synthetic')
            else:
                z.writestr(extra, 'synthetic')
    return stream.getvalue()


def test_extracts_complete_course_once(tmp_path):
    target = tmp_path / 'course'
    bootstrap.unpack_course(archive(), target, COMMIT)
    assert (target / 'config/course.yaml').read_text() == 'test fixture only'
    with pytest.raises(ValueError, match='存在しない'):
        bootstrap.unpack_course(archive(), target, COMMIT)


@pytest.mark.parametrize('name', [PREFIX + '/../outside', '/absolute', PREFIX + '/config/course.yaml', PREFIX + '/bad\\path'])
def test_rejects_archive_before_creating_destination(tmp_path, name):
    target = tmp_path / 'course'
    with pytest.raises(ValueError):
        bootstrap.unpack_course(archive(name), target, COMMIT)
    assert not target.exists()


def test_rejects_symlink(tmp_path):
    link = zipfile.ZipInfo(PREFIX + '/link')
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError, match='リンク'):
        bootstrap.unpack_course(archive(link), tmp_path / 'course', COMMIT)

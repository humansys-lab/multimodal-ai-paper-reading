"""Notebook冒頭へ埋め込む標準ライブラリだけの固定版取得処理。"""
from pathlib import Path, PurePosixPath
from io import BytesIO
from hashlib import sha256
from urllib.request import urlopen
import json
import re
import stat
import zipfile


def fetch_course(destination: Path, commit: str, expected_sha256: str) -> Path:
    """固定コミット・ハッシュ一致・安全な相対パスを確認して新しい教材フォルダを作る。"""
    if not re.fullmatch(r'[0-9a-f]{40}', commit) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('検証済みのコミットとSHA-256が設定されていません。')
    destination = destination.resolve()
    if destination.exists():
        marker = destination / '.course-release.json'
        saved = json.loads(marker.read_text()) if marker.is_file() else {}
        if saved.get('commit') != commit or saved.get('sha256') != expected_sha256 or not saved.get('files'):
            raise ValueError('既存フォルダの版が一致しません。別の空フォルダを指定してください。')
        for name, digest in saved['files'].items():
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or not target.is_file() or sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError('展開済み教材に欠落・変更があります。新しいフォルダへ取得してください。')
        return destination
    url = f'https://codeload.github.com/humansys-lab/multimodal-ai-paper-reading/zip/{commit}'
    with urlopen(url, timeout=40) as response:
        archive = response.read(20_000_001)
    if len(archive) > 20_000_000 or sha256(archive).hexdigest() != expected_sha256:
        raise ValueError('教材ZIPのサイズまたはハッシュが一致しません。展開を中止しました。')
    unpack_course(archive, destination, commit)
    files = {p.relative_to(destination).as_posix(): sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
    (destination / '.course-release.json').write_text(json.dumps({'commit': commit, 'sha256': expected_sha256, 'files': files}))
    return destination


def unpack_course(archive: bytes, destination: Path, commit: str) -> None:
    """全メンバーの確認後に展開する。既存ファイル・リンク・不正パスを拒否する。"""
    destination = destination.resolve()
    if destination.exists():
        raise ValueError('展開先はまだ存在しないフォルダを指定してください。')
    prefix = f'multimodal-ai-paper-reading-{commit}'
    with zipfile.ZipFile(BytesIO(archive)) as bundle:
        members = []; names = set(); total = 0
        for entry in bundle.infolist():
            parts = PurePosixPath(entry.filename).parts
            if not parts or parts[0] != prefix or '..' in parts or '\\' in entry.filename or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('教材ZIPに不正なパスまたはリンクがあります。')
            if entry.is_dir():
                continue
            if len(parts) < 2:
                raise ValueError('教材ZIPのフォルダ構造が不正です。')
            relative = Path(*parts[1:])
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination) or relative.as_posix() in names:
                raise ValueError('教材ZIPの範囲外・重複パスを検出しました。')
            names.add(relative.as_posix()); total += entry.file_size
            if total > 50_000_000:
                raise ValueError('教材ZIPの展開後サイズが上限を超えています。')
            members.append((entry, target))
        required = {'src/seminar_lab/__init__.py', 'config/course.yaml', 'materials/manifest.yaml', 'requirements-colab.txt'}
        if not required <= names:
            raise ValueError('教材ZIPに必要なコード・設定がありません。')
        destination.mkdir(parents=True)
        for entry, target in members:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(bundle.read(entry))

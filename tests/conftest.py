"""無害な人工設定と、全単体試験の通信禁止境界。"""
from copy import deepcopy
from pathlib import Path
import socket
import pytest
from seminar_lab.config import load_yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def model_result():
    """保存試験だけに使う人工の生成記録。実機の出力ではない。"""
    from seminar_lab.open_weight import MODEL_ID, REVISION
    return dict(model=MODEL_ID, revision=REVISION, route='open_weight_local', status='completed',
                run_id='synthetic', timestamp='2026-10-01T00:00:00Z', prompt='人工例',
                visible_template='人工例', response_raw='TEST FIXTURE ONLY',
                parameters={'max_new_tokens': 1}, elapsed_seconds=1, input_tokens=1, output_tokens=1)


def pytest_configure(config):
    """新しいチェックアウトでも、試験用ファイルは教材フォルダ内へ作る。"""
    temporary = Path(config.option.basetemp).resolve()
    if not temporary.is_relative_to(ROOT):
        raise pytest.UsageError('試験用の一時フォルダは教材フォルダ内に指定してください。')
    temporary.parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """live扱いの黙示的な通信も禁止する。"""
    def blocked(*args, **kwargs):
        raise AssertionError("API不要の試験から通信しようとしました。")
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def course():
    return load_yaml(ROOT / "config/course.yaml")


@pytest.fixture
def manifest():
    return load_yaml(ROOT / "materials/manifest.yaml")


@pytest.fixture
def adopted(course, manifest):
    """授業素材ではないテスト用人工設定。公開の採用状態は書換えない。"""
    for m in manifest["materials"]:
        if m.get("source_ref"):
            m.update(evidence_status="human_verified", scope_status="confirmed")
            continue
        m.update(adoption="adopted", evidence_status="human_verified", scope_status="confirmed", bibliography={"title": "TEST FIXTURE ONLY"})
        m["rights"]["ai_input"] = "confirmed"
        if m["id"] != "P01":
            m.update(source_version="fixture-v1", assigned_scope={"pages": [1]})
    course["common_reading"].update(source_version="fixture-v1", assigned_scope={"pages": [1], "figures": ["fixture"]}, scope_status="confirmed")
    course["homework_policy"]["status"] = "confirmed"
    course["readiness"] = {k: "pass" for k in course["readiness"]}
    extension = deepcopy(manifest["materials"][0])
    extension.update(id="E01", role="extension_paper", source_version="fixture-e1", assigned_scope={"pages": [2]})
    extension.pop("reading_ref", None)
    extension.update(bibliography={"title": "TEST FIXTURE ONLY", "authors": ["Fixture author"], "journal": "Nature"},
                     doi="10.1038/test-fixture-only-e1", source_url="https://www.nature.com/articles/test-fixture-only-e1",
                     eligibility_review={"status": "confirmed", "reviewer": "test fixture"})
    manifest["materials"].append(extension)
    return course, manifest


@pytest.fixture
def runtime():
    return {"route": "course_proxy", "api": "responses", "model": "fixture-model", "sdk_version": "fixture-sdk", "proxy_version": "fixture-proxy",
            "base_url": "https://example.invalid/v1", "allowed_base_urls": ["https://example.invalid/v1"], "max_retries": 0, "timeout_seconds": 30,
            "capabilities": {"input_kinds": ["text", "image", "pdf"], "manual_history": True,
                             "parameters": {"max_output_tokens": {"min": 1, "max": 500}}},
            "audit": {"verified_at": "fixture-only", "evidence_id": "fixture-only", "route_test": "pass", "retention_review": "pass", "budget_fail_closed": "pass"}}

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4
import pytest
from seminar_lab.client import ERRORS, LivePermission, Session, TransportError
from seminar_lab.config import ValidationError, material_context
from seminar_lab.inputs import text_input
from seminar_lab.records import new_record, save_records, load_records

RESPONSE = json.loads((Path(__file__).parent / "fixtures/response.json").read_text())


class FakeTransport:
    """人工応答はtests内だけ。実測の証拠にしない。"""
    def __init__(self, error=None, response=None):
        self.calls = []
        self.error = error
        self.response = RESPONSE if response is None else response

    def send(self, payload):
        self.calls.append(deepcopy(payload))
        if self.error:
            raise self.error
        return deepcopy(self.response)


def run(session, runtime, adopted, transport, mode="new", run_id=None, aid="P1"):
    return session.run(runtime=runtime, context=material_context(*adopted, aid), prompt="試験用の問い", inputs=[text_input("試験用", "fixture p1")],
                       mode=mode, parameters={"max_output_tokens":100}, run_id=run_id or str(uuid4()), transport=transport)


def test_continuation_new_duplicate_and_session_separation(runtime, adopted):
    s, other, fake = Session(), Session(), FakeTransport()
    record = run(s, runtime, adopted, fake, run_id="one")
    assert record["status"] == "success" and record["cost_value"] is None
    with pytest.raises(ValidationError): run(s, runtime, adopted, fake, run_id="one")
    assert len(fake.calls) == 1
    record2 = run(s, runtime, adopted, fake, mode="continue")
    assert record2["prior_turn_count"] == 1 and len(fake.calls[-1]["input"]) == 3
    run(s, runtime, adopted, fake, mode="new", aid="P2a")
    assert len(fake.calls[-1]["input"]) == 1 and other.history == []
    assert s.session_id != other.session_id
    assert fake.calls[-1]["store"] is False and fake.calls[-1]["truncation"] == "disabled"
    assert all(x["role"] != "system" for x in fake.calls[-1]["input"])


@pytest.mark.parametrize("kind", ["timeout", "authentication", "budget", "rate_limit", "invalid_input", "network", "service_unavailable"])
def test_failures_do_not_commit_fallback_retry_or_claim_zero(runtime, adopted, kind):
    s = Session()
    run(s, runtime, adopted, FakeTransport())
    history = s.history
    f = FakeTransport(TransportError(kind))
    r = run(s, runtime, adopted, f, mode="continue", run_id="failed")
    assert r["status"] == "failed" and r["error_type"] == kind
    assert r["cost_value"] is None and r["cost_kind"] == "unknown" and r["retry_count"] == 0
    assert s.history == history and len(f.calls) == 1
    with pytest.raises(ValidationError): run(s, runtime, adopted, f, run_id="failed")


def test_exception_secrets_not_logged(runtime, adopted):
    marker = "synthetic-secret-never-print"
    r = run(Session(), runtime, adopted, FakeTransport(RuntimeError(marker + " Authorization: header")))
    assert marker not in json.dumps(r) and r["response_raw"] is None


def test_partial_response_saved_not_committed(runtime, adopted):
    s = Session()
    partial = {**RESPONSE, "status":"incomplete"}
    r = run(s, runtime, adopted, FakeTransport(response=partial))
    assert r["status"] == "incomplete" and r["response_raw"]["output"]
    assert s.history == []


def test_context_change_requires_new(runtime, adopted):
    s = Session()
    run(s,runtime,adopted,FakeTransport())
    changed = deepcopy(adopted)
    changed[0]["common_reading"]["source_version"] = "different"
    with pytest.raises(ValidationError): run(s,runtime,changed,FakeTransport(),mode="continue")
    runtime["model"] = "another-model"
    with pytest.raises(ValidationError): run(s,runtime,adopted,FakeTransport(),mode="continue")


def test_r0_no_api(runtime, adopted):
    f=FakeTransport()
    with pytest.raises(ValidationError): run(Session(),runtime,adopted,f,aid="P0")
    assert f.calls == []


def test_permission_reserves_count_even_if_no_response(runtime):
    p = LivePermission("teacher", "fixture test only", runtime["route"], runtime["model"], "fixture individual key", 0.1, 1)
    p.consume(runtime)
    with pytest.raises(ValidationError): p.consume(runtime)


@pytest.mark.parametrize("suffix", [".md", ".jsonl"])
def test_lossless_unicode_null_raw_and_revision(tmp_path, adopted, suffix):
    r = new_record(material_context(*adopted,"P0"))
    r.update(student_explanation="日本語 / α → 図1\n```\n", student_revision="修正した本人の文", future_field={"a":[None,"unknown"]})
    path=tmp_path/('record'+suffix)
    save_records([r],path)
    assert load_records(path)==[r]
    with pytest.raises(FileExistsError): save_records([r],path)


def test_transfer_cannot_overwrite_r_phases(tmp_path, adopted):
    r = new_record(material_context(*adopted, "HW1", "E01"))
    r["phase"]="R1"
    with pytest.raises(ValidationError): save_records([r],tmp_path/'bad.jsonl')


def test_unknown_cost_not_zero(tmp_path, adopted):
    r=new_record(material_context(*adopted,"P0"));r["cost_value"]=0
    with pytest.raises(ValidationError):save_records([r],tmp_path/'bad.md')


def test_record_embedded_markdown_delimiters_roundtrip(tmp_path, adopted):
    r = new_record(material_context(*adopted, "P0"))
    r["student_explanation"] = '<!-- SEMINAR_RECORDS -->\n```json\n[]\n```\n<!-- END_SEMINAR_RECORDS -->'
    path = tmp_path/'record.md'
    save_records([r], path)
    assert load_records(path) == [r]


def test_exact_sent_excerpt_and_history_saved(runtime, adopted):
    s, f = Session(), FakeTransport()
    run(s, runtime, adopted, f)
    r = run(s, runtime, adopted, f, mode="continue")
    assert r["request_input"] == f.calls[-1]["input"]
    assert r["request_input"][0]["content"][0]["text"] == "試験用"


def test_raw_upstream_error_is_sanitized(runtime, adopted):
    raw = {**RESPONSE, "status": "failed", "error": {"message": "synthetic-secret-header"}}
    session = Session()
    r = run(session, runtime, adopted, FakeTransport(response=raw))
    assert "synthetic-secret-header" not in json.dumps(r)
    assert r["status"] == "failed" and session.history == []


def test_simultaneous_same_session_request_is_rejected(runtime, adopted):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered, release = Event(), Event()
    class BlockingTransport(FakeTransport):
        def send(self, payload):
            entered.set()
            assert release.wait(5)
            return super().send(payload)
    s, f = Session(), BlockingTransport()
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(run, s, runtime, adopted, f)
        assert entered.wait(5)
        try:
            with pytest.raises(ValidationError):
                run(s, runtime, adopted, f)
        finally:
            release.set()
        assert first.result()["status"] == "success"
    assert len(f.calls) == 1


@pytest.mark.parametrize("change,kind", [
    ({"model": "unrequested-model"}, "model_mismatch"),
    ({"output": []}, "invalid_response"),
    ({"output": [{"type": "function_call", "name": "unexpected_tool"}]}, "invalid_response"),
    ({"output": [{"type": "message", "role": "assistant", "content": [{"type": "refusal", "refusal": "declined"}]}]}, "refusal"),
    ({"output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "  "}]}]}, "invalid_response"),
    ({"output": [{"type": "message", "role": "assistant", "content": "malformed"}]}, "invalid_response"),
    ({"output": [{"type": "reasoning", "summary": []}]}, "invalid_response"),
])
def test_unexpected_response_is_not_success_or_history(runtime, adopted, change, kind):
    session = Session()
    run(session, runtime, adopted, FakeTransport())
    before = session.history
    fake = FakeTransport(response={**deepcopy(RESPONSE), **change})
    record = run(session, runtime, adopted, fake, mode="continue")
    assert record["status"] == "failed" and record["error_type"] == kind
    assert session.history == before and len(fake.calls) == 1
    assert record["response_raw"] is not None and record["cost_value"] is None


@pytest.mark.parametrize("limit", [float("nan"), float("inf"), -1, 0, True])
def test_nonfinite_or_invalid_budget_cannot_authorize(runtime, limit):
    permission = LivePermission("teacher", "fixture", runtime["route"], runtime["model"], "fixture", limit, 1)
    with pytest.raises(ValidationError):
        permission.consume(runtime)
    assert permission.used == 0


def test_shared_permission_enforces_one_total_across_threads(runtime):
    from concurrent.futures import ThreadPoolExecutor
    permission = LivePermission("teacher", "fixture", runtime["route"], runtime["model"], "fixture", 1, 1)
    def reserve(_):
        try:
            permission.consume(runtime)
            return True
        except ValidationError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(32))) == 1
    assert permission.used == 1


def test_input_kind_cannot_hide_an_unsupported_attachment(runtime):
    from seminar_lab.inputs import PreparedInput
    spoof = PreparedInput("text", {"type": "input_file", "file_data": "data:application/pdf;base64,YQ==", "filename": "x.pdf"}, {})
    with pytest.raises(ValidationError):
        Session().preview(runtime, "question", [spoof], "new", {"max_output_tokens": 100})

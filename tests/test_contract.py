from copy import deepcopy
from pathlib import Path
import pytest
from seminar_lab.config import COMMON, ValidationError, check_course, material_context, validate_runtime
from seminar_lab.ui import activity_view

ROOT = Path(__file__).resolve().parents[1]


def test_unconfirmed_scope_and_evidence_allow_structure_but_not_release(course, manifest):
    # 教員の承認が進んでも、未確認のケースを明示して検査する。
    course["common_reading"]["scope_status"] = "proposed"
    manifest["materials"][0]["evidence_status"] = "agent_draft"
    assert check_course(course, manifest, ROOT) == []
    errors = check_course(course, manifest, ROOT, "readiness")
    assert any("教員確認" in s for s in errors)
    assert any("指定範囲は提案" in s for s in errors)
    assert not any("採用数" in s for s in errors)


def test_positive_readiness_uses_only_artificial_fixture(adopted):
    assert check_course(*adopted, ROOT, "readiness") == []


def test_delegated_evidence_does_not_approve_rights_or_live_tests(course, manifest):
    # 根拠表の確認だけでは、明示的に未確認の入力条件を解除しない。
    next(m for m in manifest["materials"] if m["id"] == "P01")["rights"]["ai_input"] = "unconfirmed"
    errors = check_course(course, manifest, ROOT, "readiness")
    assert not any("根拠表" in error and any(f'{mid}の' in error for mid in ('P01', 'V01', 'V02')) for error in errors)
    assert any('P02の根拠表' in error for error in errors)
    assert any('M01の根拠表' in error for error in errors)
    assert any("AI入力権利" in error for error in errors)
    assert any("not_run" in error for error in errors)


@pytest.mark.parametrize("change", ["no_review", "no_delegation", "other_delegation", "unreviewed",
                                  "failed", "hash", "version", "extra_rows", "missing_row", "wrong_material"])
def test_delegated_evidence_is_limited_to_reviewed_source_and_scope(course, manifest, change):
    material = next(m for m in manifest["materials"] if m["id"] == "V02")
    if change == "no_review":
        material.pop("evidence_review")
    elif change == "no_delegation":
        material["evidence_review"].pop("decision_id")
    elif change == "other_delegation":
        material["evidence_review"]["decision_id"] = "UNCONFIRMED"
    elif change == "unreviewed":
        material["evidence_status"] = "agent_draft"
    elif change == "failed":
        material["evidence_review"]["result"] = "fail"
    elif change == "hash":
        manifest["materials"][0]["file_hash"] = "different-source"
    elif change == "version":
        course["common_reading"]["source_version"] = "different-version"
    elif change == "extra_rows":
        material["evidence_review"]["rows"].append("F3")
    elif change == "missing_row":
        material["evidence_review"]["rows"] = ["F1"]
    elif change == "wrong_material":
        manifest["materials"][0].update(evidence_status=material["evidence_status"],
                                        evidence_review=deepcopy(material["evidence_review"]))
    errors = check_course(course, manifest, ROOT, "readiness")
    assert any("根拠表" in error for error in errors)


@pytest.mark.parametrize("aid", sorted(COMMON))
def test_common_contract_is_single_and_has_no_choice(adopted, aid):
    c, m = adopted
    ctx = material_context(c, m, aid)
    assert ctx["material_id"] == "P01"
    assert all(ctx[k] == c["common_reading"][k] for k in ("source_version", "assigned_scope", "question_set_id"))
    assert "choices" not in activity_view(c, m, aid)
    for bad in ("E01", "U_test", "V01"):
        with pytest.raises(ValidationError):
            material_context(c, m, aid, bad)


def test_unconfirmed_input_rights_rejected(course, manifest):
    next(m for m in manifest["materials"] if m["id"] == "P01")["rights"]["ai_input"] = "unconfirmed"
    with pytest.raises(ValidationError):
        material_context(course, manifest, "P1")


@pytest.mark.parametrize("mid", ["E01", "U_local"])
def test_homework_paths_do_not_replace_common(adopted, mid):
    c, m = adopted
    before = deepcopy(c["common_reading"])
    local = deepcopy(m["materials"][-1])
    local.update(id="U_local", input_review={"status": "confirmed", "reviewer": "本人"})
    ctx = material_context(c, m, "HW1", mid, local)
    assert ctx["phase"] == "homework" and c["common_reading"] == before
    if mid.startswith("U_"):
        assert ctx["adoption"] == "not_applicable" and ctx["publication"] == "not_granted"
    assert "choices" in activity_view(c, m, "HW1")


def test_student_unconfirmed_and_vlm_homework_rejected(adopted):
    c, m = adopted
    with pytest.raises(ValidationError):
        material_context(c, m, "HW1", "U_local", {"id": "U_local"})
    with pytest.raises(ValidationError):
        material_context(c, m, "HW1", "V01")


@pytest.mark.parametrize("change", ["time", "break", "phase", "choice", "duplicate_contract", "questions", "two_common", "segments"])
def test_course_mutations_are_detected(adopted, change):
    c, m = adopted
    if change == "time": c["days"][0]["blocks"][0]["start"] = "09:00"
    elif change == "break": c["days"][0]["blocks"][2]["kind"] = "teaching"
    elif change == "phase": c["activities"]["P1"]["phase"] = "R2"
    elif change == "choice": c["activities"]["P1"]["material_choice"] = True
    elif change == "duplicate_contract": c["activities"]["P1"]["source_version"] = "other"
    elif change == "questions": c["question_sets"]["Q_COMMON_3"][0] = "extra task"
    elif change == "two_common": m["materials"].append({**m["materials"][0], "id": "P02"})
    elif change == "segments": c["activities"]["V1"]["segments_minutes"] = [10, 5]
    assert check_course(c, m, ROOT)


@pytest.mark.parametrize("field,value", [("model",None),("api","chat"),("max_retries",2),("base_url","https://other.invalid/v1"),("timeout_seconds",0)])
def test_runtime_rejects_unset_and_unsupported(runtime, field, value):
    runtime[field] = value
    with pytest.raises(ValidationError):
        validate_runtime(runtime, {"text"}, {"max_output_tokens": 100})


@pytest.mark.parametrize("key", ["route_test", "budget_fail_closed", "retention_review"])
def test_route_checks_fail_closed(runtime, key):
    runtime["audit"][key] = "not_run"
    with pytest.raises(ValidationError):
        validate_runtime(runtime, {"text"}, {"max_output_tokens": 100})


def test_unsupported_settings_not_silently_rewritten(runtime):
    for params in [{"max_output_tokens":100,"thinking":"high"}, {"max_output_tokens":999}, {"max_output_tokens":True}]:
        with pytest.raises(ValidationError):
            validate_runtime(runtime, {"text"}, params)
    with pytest.raises(ValidationError):
        validate_runtime(runtime, {"video"}, {"max_output_tokens":100})


def test_wrong_dates_or_exercise_positions_are_detected(adopted):
    c, m = adopted
    c["days"][0]["date"] = "2026-10-04"
    assert check_course(c, m, ROOT)
    c["days"][0]["date"] = "2026-10-03"
    timeline = c["days"][0]["timeline"]
    timeline[2]["activity_id"], timeline[6]["activity_id"] = timeline[6]["activity_id"], timeline[2]["activity_id"]
    assert check_course(c, m, ROOT)


@pytest.mark.parametrize("section,field,value", [
    ("capabilities", "silent_setting", True),
    ("audit", "unrecognized_audit", "pass"),
    ("capabilities", "parameters", {"max_output_tokens": {"min": 1, "max": float("inf")}}),
    ("capabilities", "parameters", {"max_output_tokens": {"minimum": 1, "maximum": 500}}),
])
def test_unknown_nested_configuration_is_rejected(runtime, section, field, value):
    runtime[section][field] = value
    with pytest.raises(ValidationError):
        validate_runtime(runtime, {"text"}, {"max_output_tokens": 100})

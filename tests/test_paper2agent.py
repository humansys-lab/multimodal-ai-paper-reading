"""同じ掲載版の図の再利用と、別論文への学習の転用を検査する。通信なし。"""
from copy import deepcopy

import pytest

from seminar_lab.config import ValidationError, material_context, resolve_material
from seminar_lab.records import new_record, save_records, load_records


def test_all_figure_activities_inherit_paper_identity(adopted):
    course, manifest = adopted
    paper = resolve_material(course, manifest, "P01")
    for aid in ("V1", "V2", "V3", "V4"):
        figure = material_context(course, manifest, aid)
        assert figure["source_material_id"] == "P01"
        assert figure["assigned_scope"] != paper["assigned_scope"]
        for field in ("source_version", "file_hash", "doi", "rights", "bibliography"):
            assert figure[field] == paper[field]
    course["common_reading"]["source_version"] = "changed-test-version"
    assert resolve_material(course, manifest, "V02")["source_version"] == "changed-test-version"


@pytest.mark.parametrize("override", [{"source_ref": "T01"}, {"source_version": "other"},
                                      {"rights": {"ai_input": "confirmed"}}, {"license": {"id": "CC0"}}])
def test_figure_source_cannot_be_replaced(adopted, override):
    course, manifest = adopted
    manifest["materials"][1].update(override)
    with pytest.raises(ValidationError):
        resolve_material(course, manifest, "V01")


def test_p01_continuation_is_separate_from_required_new_paper(adopted):
    course, manifest = adopted
    with pytest.raises(ValidationError, match="別論文"):
        material_context(course, manifest, "HW1", "P01")
    context = material_context(course, manifest, "P01_REVIEW")
    assert context["phase"] == "homework" and context["material_id"] == "P01"
    assert context["assigned_scope"] == course["common_reading"]["assigned_scope"]


@pytest.mark.parametrize("patch", [
    {"bibliography": {"title": "Fixture", "authors": ["Fixture"], "journal": "Unapproved journal"}},
    {"open_access": False}, {"publication_status": "preprint"}, {"article_type": "news"},
    {"eligibility_review": {"status": "unconfirmed", "reviewer": "本人"}},
    {"source_url": "https://www.science.org/doi/10.1038/test-fixture-only"},
    {"doi": None},
])
def test_homework_rejects_ineligible_material(adopted, patch):
    course, manifest = adopted
    material = manifest["materials"][-1]
    material.update(patch)
    with pytest.raises(ValidationError):
        material_context(course, manifest, "HW1", "E01")


def test_p01_cannot_be_relabelled_as_new_student_paper(adopted):
    course, manifest = adopted
    local = deepcopy(manifest["materials"][-1])
    local.update(id="U_duplicate", doi=course["homework_policy"]["common_doi"].upper(),
                 input_review={"status": "confirmed", "reviewer": "本人"})
    with pytest.raises(ValidationError, match="別論文"):
        material_context(course, manifest, "HW1", local["id"], local)


def test_unconfirmed_journal_policy_prevents_send(adopted):
    course, manifest = adopted
    course["homework_policy"]["status"] = "proposed"
    # 草稿の閲覧は可能。送信許可とは別。
    assert material_context(course, manifest, "HW1", "E01", for_input=False)
    with pytest.raises(ValidationError, match="対象誌条件"):
        material_context(course, manifest, "HW1", "E01")


@pytest.mark.parametrize("suffix", [".md", ".jsonl"])
def test_paper_identity_and_student_review_survive_save(adopted, tmp_path, suffix):
    course, manifest = adopted
    context = material_context(course, manifest, "HW1", "E01")
    record = new_record(context)
    path = tmp_path / ("reading" + suffix)
    save_records([record], path)
    loaded = load_records(path)[0]
    for field in ("bibliography", "doi", "source_url", "source_version", "file_hash", "eligibility_review"):
        assert loaded[field] == context[field]
    assert loaded["source_material_id"] == "E01"
    assert loaded["source_file_hash"] == context["file_hash"]


def test_science_original_article_is_allowed_by_proposed_two_journal_rule(adopted):
    course, manifest = adopted
    paper = manifest["materials"][-1]
    paper["bibliography"]["journal"] = "Science"
    paper.update(doi="10.1126/science.test-fixture-only", source_url="https://www.science.org/doi/10.1126/science.test-fixture-only")
    assert material_context(course, manifest, "HW1", "E01")["bibliography"]["journal"] == "Science"

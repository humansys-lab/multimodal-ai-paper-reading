"""設定の二重指定・構文不正で黙示的な上書きや秘密の表示をしない。"""
import pytest

from seminar_lab.config import ValidationError, load_yaml, validate_runtime


@pytest.mark.parametrize("content", [
    "model: first\nmodel: second\n",
    "capabilities:\n  manual_history: true\n  manual_history: false\n",
    "defaults: &defaults {model: first}\nsettings: {<<: *defaults, model: second}\n",
])
def test_duplicate_or_merged_settings_stop(tmp_path, content):
    path = tmp_path / "runtime.yaml"
    path.write_text(content)
    with pytest.raises(ValidationError):
        load_yaml(path)
    assert path.read_text() == content


def test_yaml_error_does_not_show_secret_line(tmp_path):
    path = tmp_path / "runtime.yaml"
    path.write_text("value: [fixture-sensitive-value\n")
    with pytest.raises(ValidationError) as caught:
        load_yaml(path)
    assert "fixture-sensitive-value" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_runtime_version_requires_integer(runtime, version):
    runtime["schema_version"] = version
    with pytest.raises(ValidationError):
        validate_runtime(runtime, {"text"}, {"max_output_tokens": 100})


@pytest.mark.parametrize("name", ["temperature", "top_p"])
@pytest.mark.parametrize("value", [True, False, "1", float("nan"), float("inf")])
def test_numeric_parameters_reject_bool_text_and_nonfinite(runtime, name, value):
    # values方式でもPythonのTrue == 1、False == 0を許可しない。
    runtime["capabilities"]["parameters"][name] = {"values": [0, 1, value]}
    with pytest.raises(ValidationError):
        validate_runtime(runtime, {"text"}, {"max_output_tokens": 100, name: value})


@pytest.mark.parametrize("name", ["temperature", "top_p"])
def test_confirmed_finite_numeric_parameter_is_accepted(runtime, name):
    runtime["capabilities"]["parameters"][name] = {"values": [0, 0.7, 1]}
    validate_runtime(runtime, {"text"}, {"max_output_tokens": 100, name: 0.7})

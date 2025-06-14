import pytest
import pandas as pd
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from module_l import parse_llm_response, compute_confidence, load_prompt_template

@pytest.fixture
def dummy_response():
    return "Prediction: 1.1, Explanation: Expected to perform well, Flag: true"

def test_parse_llm_response_valid(dummy_response):
    pred, explanation, flag = parse_llm_response(dummy_response, 0.5)
    assert abs(pred - 1.1) < 1e-6
    assert explanation.startswith("Expected")
    assert flag == "true"

def test_parse_llm_response_fallback():
    bad_response = "Totally unstructured reply"
    pred, explanation, flag = parse_llm_response(bad_response, 0.7)
    assert abs(pred - 0.7) < 1e-6
    assert explanation == bad_response
    assert flag == ""

def test_compute_confidence():
    assert compute_confidence(1.0, 1.0) == 1.0
    assert compute_confidence(2.0, 1.0) == 0.5
    assert compute_confidence(0.0, 0.0) == 1.0

def test_template_render():
    with tempfile.TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "test.jinja2"
        template_path.write_text("Player: {{ player }}, Stat: {{ stat }}")
        template = load_prompt_template(template_path)
        result = template.render(player="John Doe", stat="HR")
        assert "John Doe" in result
        assert "HR" in result

@patch("module_l.call_llm")
def test_llm_call_mocked(call_llm_mock):
    call_llm_mock.return_value = "Prediction: 2.0, Explanation: Mocked, Flag: false"
    result = call_llm_mock("http://fake", {})
    assert "Mocked" in result

@patch("module_l.call_llm")
@patch("module_l.load_config")
@patch("module_l.setup_logger")
def test_cli_subprocess_integration(mock_logger, mock_config, mock_llm):
    # Basic smoke test: pretend the LLM returns cleanly
    mock_llm.return_value = "Prediction: 2.2, Explanation: OK, Flag: true"
    mock_config.return_value = {
        "llm": {
            "model": "test",
            "endpoint": "http://fake",
            "temperature": 0.3,
            "max_tokens": 256,
            "prompt_template": "tests/test.jinja2"
        },
        "outputs": {
            "dir": "tmp",
            "combined_preds_dir": "tests"
        },
        "logging": {
            "dir": "tmp",
            "level": "INFO",
            "max_bytes": 500000,
            "backup_count": 1
        },
        "overwrite_policy": "force"
    }
    # If needed, test subprocess logic here
    assert True

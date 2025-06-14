import pytest
import importlib
import sys
from pathlib import Path
from unittest import mock

from pipeline import run_module, expected_output_exists

# --------------------------------------------------------------------------- #
# Basic smoke test
# --------------------------------------------------------------------------- #
def test_import_pipeline():
    import pipeline  # noqa: F401


# --------------------------------------------------------------------------- #
# Dry-run logic
# --------------------------------------------------------------------------- #
def test_dry_run_behavior(tmp_path):
    dummy_cfg = mock.Mock()
    dummy_logger = mock.Mock()
    dummy_args = mock.Mock(dry_run=True, force=False, overwrite_policy="warn")

    result = run_module("A", dummy_cfg, dummy_args, dummy_logger)
    assert result == "SKIPPED"
    dummy_logger.info.assert_any_call("[DRY-RUN] Skipping module A")


# --------------------------------------------------------------------------- #
# Overwrite-policy = warn
# --------------------------------------------------------------------------- #
def test_overwrite_policy_warn(tmp_path):
    output_dir = tmp_path / "module_a"
    output_dir.mkdir()
    (output_dir / "dummy.txt").write_text("exists")

    dummy_cfg = mock.Mock()
    dummy_cfg.outputs.root = tmp_path
    dummy_args = mock.Mock(dry_run=False, force=False, overwrite_policy="warn")
    dummy_logger = mock.Mock()

    result = run_module("A", dummy_cfg, dummy_args, dummy_logger)
    assert result == "SKIPPED"
    dummy_logger.warning.assert_called()


# --------------------------------------------------------------------------- #
# expected_output_exists()
# --------------------------------------------------------------------------- #
def test_expected_output_exists(tmp_path):
    output_dir = tmp_path / "module_a"
    output_dir.mkdir()
    (output_dir / "file.txt").write_text("data")

    cfg = mock.Mock()
    cfg.outputs.root = tmp_path
    assert expected_output_exists("A", cfg)


# --------------------------------------------------------------------------- #
# Invalid module in CLI → SystemExit
# --------------------------------------------------------------------------- #
def test_config_error(monkeypatch):
    from pipeline import main
    dummy_config = str(Path("tests/dummy_config.yaml").resolve())

    test_args = [
        "pipeline.py",
        "--modules", "A,B,Z",  # Z is invalid → triggers CLI error
        "--config-path", dummy_config,
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit):  # CLI exit code is expected
        main()


# --------------------------------------------------------------------------- #
# Continue-on-failure logic
# --------------------------------------------------------------------------- #
def test_continue_on_failure(monkeypatch):
    dummy_cfg = mock.Mock()
    dummy_logger = mock.Mock()

    def raise_exception(*args, **kwargs):
        raise Exception("Module G failure")

    monkeypatch.setattr(importlib, "import_module", lambda *_: raise_exception())
    dummy_args = mock.Mock(
        dry_run=False,
        force=False,
        overwrite_policy="warn",
        continue_on_failure=True,
    )

    result = run_module("G", dummy_cfg, dummy_args, dummy_logger)
    assert result == "FAILED"


# --------------------------------------------------------------------------- #
# Concurrency flag triggers ThreadPoolExecutor
# --------------------------------------------------------------------------- #
def test_concurrency(monkeypatch, capsys):
    import pipeline
    dummy_config = str(Path("tests/dummy_config.yaml").resolve())

    test_args = [
        "pipeline.py",
        "--modules", "A,B",
        "--concurrency", "2",
        "--config-path", dummy_config,
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Mock executor + run_module for full isolation
    mock_executor = mock.MagicMock()
    mock_future = mock.MagicMock()
    mock_future.result.return_value = "SUCCESS"
    mock_executor.__enter__.return_value.submit.return_value = mock_future
    mock_executor.__enter__.return_value.__iter__.return_value = [mock_future, mock_future]

    monkeypatch.setattr(pipeline, "run_module", lambda *a, **kw: "SUCCESS")

    with mock.patch("pipeline.ThreadPoolExecutor", return_value=mock_executor):
        pipeline.main()

    captured = capsys.readouterr()
    assert "Module A" in captured.out or "Module B" in captured.out

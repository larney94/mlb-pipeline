import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from utils.logging_utils import get_rotating_logger


from module_b import download_static_csvs

@pytest.fixture
def dummy_config(tmp_path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    return {
        "outputs": {"static_dir": str(static_dir)},
        "overwrite_policy": "force",
        "static_csvs": [
            {
                "name": "test_dataset",
                "url": "https://people.sc.fsu.edu/~jburkardt/data/csv/addresses.csv"
            }
        ]
    }

def test_download_static_csvs_success(dummy_config):
    download_static_csvs(dummy_config)
    expected_file = Path(dummy_config["outputs"]["static_dir"]) / "test_dataset.csv"
    assert expected_file.exists()
    assert expected_file.read_text() != ""

def test_download_static_csvs_missing_url(dummy_config):
    dummy_config["static_csvs"] = [{"name": "bad_entry"}]
    download_static_csvs(dummy_config)
    assert not any(Path(dummy_config["outputs"]["static_dir"]).glob("*.csv"))

def test_download_static_csvs_overwrite_policy_warn(tmp_path):
    static_file = tmp_path / "static" / "test_dataset.csv"
    static_file.parent.mkdir(parents=True, exist_ok=True)
    static_file.write_text("existing content")

    cfg = {
        "outputs": {"static_dir": str(static_file.parent)},
        "overwrite_policy": "warn",
        "static_csvs": [{
            "name": "test_dataset",
            "url": "https://people.sc.fsu.edu/~jburkardt/data/csv/addresses.csv"
        }]
    }
    download_static_csvs(cfg)
    assert static_file.read_text() == "existing content"

@patch("requests.get")
def test_download_static_csvs_failed_download(mock_get, dummy_config):
    mock_get.side_effect = Exception("Download error")
    download_static_csvs(dummy_config)
    output_file = Path(dummy_config["outputs"]["static_dir"]) / "test_dataset.csv"
    assert not output_file.exists()

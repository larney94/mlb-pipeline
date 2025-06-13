import pytest
from unittest import mock
from pathlib import Path
import pandas as pd
import shutil

import module_e as me

TEST_DIR = Path("tests/tmp_test_starters")
TEST_FILE = TEST_DIR / "starters_2024-06-14.csv"

MOCK_STARTERS = [
    {
        'player_id': '123',
        'player_name': 'John Doe',
        'position': 'SP',
        'team': 'Yankees',
        'slot': 'home',
        'game_date': '2024-06-14',
    }
]

@pytest.fixture(autouse=True)
def setup_and_teardown():
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(TEST_DIR, ignore_errors=True)

def test_write_starters_force():
    me.write_starters_file(MOCK_STARTERS, TEST_FILE, overwrite='force')
    df = pd.read_csv(TEST_FILE)
    assert len(df) == 1
    assert df.loc[0, 'player_name'] == 'John Doe'

def test_write_starters_warn():
    TEST_FILE.write_text("already exists")
    me.write_starters_file(MOCK_STARTERS, TEST_FILE, overwrite='warn')
    assert TEST_FILE.read_text() == "already exists"

def test_write_starters_error():
    TEST_FILE.write_text("exists")
    with pytest.raises(FileExistsError):
        me.write_starters_file(MOCK_STARTERS, TEST_FILE, overwrite='error')

def test_fetch_starters_mocked():
    with mock.patch('statsapi.schedule') as mock_schedule:
        mock_schedule.return_value = [
            {
                'homeProbablePitcher': {'id': '123', 'fullName': 'John Doe', 'primaryPosition': {'abbreviation': 'SP'}},
                'homeName': 'Yankees',
                'awayProbablePitcher': {'id': '456', 'fullName': 'Jane Smith', 'primaryPosition': {'abbreviation': 'SP'}},
                'awayName': 'Red Sox'
            }
        ]
        starters = me.fetch_starters('2024-06-14', 0)
        assert len(starters) == 2
        names = {s['player_name'] for s in starters}
        assert 'John Doe' in names
        assert 'Jane Smith' in names

def test_empty_schedule():
    with mock.patch('statsapi.schedule', return_value=[]):
        starters = me.fetch_starters('2024-06-14', 0)
        assert starters == []

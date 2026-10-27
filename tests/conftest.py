import shutil
from pathlib import Path

import pytest

from termquake.build import build_database
from termquake.config import REPO_ROOT, Paths, load_config

FIXTURE_RAW = Path(__file__).parent / "fixtures" / "raw"


@pytest.fixture
def config():
    return load_config(REPO_ROOT / "termquake.toml")


@pytest.fixture
def workspace(tmp_path) -> Paths:
    """An isolated copy of the repository layout, so tests never touch real outputs."""
    shutil.copytree(REPO_ROOT / "db", tmp_path / "db")
    shutil.copytree(FIXTURE_RAW, tmp_path / "data" / "raw")
    shutil.copy(REPO_ROOT / "termquake.toml", tmp_path / "termquake.toml")
    return Paths(tmp_path)


@pytest.fixture
def built(config, workspace):
    stats = build_database(config, workspace)
    return workspace, stats

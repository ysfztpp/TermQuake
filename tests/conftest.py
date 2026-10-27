import shutil
from pathlib import Path

import pytest

from termquake.build import migrate
from termquake.config import REPO_ROOT, Paths, load_config

FIXTURE_LEGACY = Path(__file__).parent / "fixtures" / "legacy"


@pytest.fixture
def config():
    return load_config(REPO_ROOT / "termquake.toml")


@pytest.fixture
def workspace(tmp_path) -> Paths:
    """An isolated copy of the repository layout, so tests never touch real data."""
    shutil.copytree(REPO_ROOT / "db", tmp_path / "db")
    shutil.copytree(FIXTURE_LEGACY, tmp_path / "data" / "legacy")
    shutil.copy(REPO_ROOT / "termquake.toml", tmp_path / "termquake.toml")
    return Paths(tmp_path)


@pytest.fixture
def migrated(config, workspace):
    """Workspace after the one-time migration (which also builds and dumps)."""
    stats = migrate(config, workspace)
    return workspace, stats

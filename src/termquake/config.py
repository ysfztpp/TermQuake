"""Load termquake.toml and resolve repository paths."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# Repository root when running from a source checkout (editable install, tests).
REPO_ROOT = Path(__file__).resolve().parents[2]


def find_root(start: Path | None = None) -> Path:
    """The repository root: the nearest directory with termquake.toml, from cwd upwards.

    Works whether the package is installed in editable mode or into site-packages.
    """
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        if (directory / "termquake.toml").exists():
            return directory
    if (REPO_ROOT / "termquake.toml").exists():
        return REPO_ROOT
    raise FileNotFoundError("termquake.toml not found: run termquake inside the repository")


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def db_dir(self) -> Path:
        """Schema, seed data and triggers (code)."""
        return self.root / "db"

    @property
    def data_db(self) -> Path:
        """The database's canonical content, one SQL file per table (data)."""
        return self.root / "data" / "db"

    @property
    def legacy(self) -> Path:
        """Frozen snapshot of the legacy Google Sheet."""
        return self.root / "data" / "legacy"

    @property
    def qa_report(self) -> Path:
        return self.root / "data" / "QA_REPORT.md"

    @property
    def build(self) -> Path:
        return self.root / "build"

    @property
    def database(self) -> Path:
        return self.build / "termquake.db"

    @property
    def site_public(self) -> Path:
        return self.root / "site" / "public"


@dataclass(frozen=True)
class Config:
    languages: list[str]  # published language codes, in display order
    pivot: str
    legacy_sheet_id: str
    tabs: dict[str, str]  # legacy sheet tab name -> snapshot file stem
    columns: dict[str, str]  # English language name -> code
    domains: dict[str, str]  # domain label -> domain code
    phrase_labels: list[str]

    @property
    def legacy_sheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.legacy_sheet_id}"


def load_config(path: Path | None = None) -> Config:
    path = path or REPO_ROOT / "termquake.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    languages = list(raw["publish"]["languages"])
    pivot = raw["publish"].get("pivot", languages[0])
    if pivot not in languages:
        raise ValueError(f"publish.pivot '{pivot}' must be one of publish.languages")
    legacy = raw["legacy"]
    return Config(
        languages=languages,
        pivot=pivot,
        legacy_sheet_id=legacy["sheet_id"],
        tabs=dict(legacy["tabs"]),
        columns=dict(legacy["columns"]),
        domains=dict(legacy["domains"]),
        phrase_labels=list(legacy["entry_types"]["phrase_labels"]),
    )

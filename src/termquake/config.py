"""Load termquake.toml and resolve repository paths."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# Repository root when running from a source checkout (editable install, tests).
REPO_ROOT = Path(__file__).resolve().parents[2]


def find_root(start: Path | None = None) -> Path:
    """The repository root: the nearest directory with termquake.toml, from cwd upwards."""
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
    def schema(self) -> Path:
        """The table definitions."""
        return self.root / "db" / "schema.sql"

    @property
    def data_db(self) -> Path:
        """The database's content, one SQL file per table: the source of truth."""
        return self.root / "data" / "db"

    @property
    def legacy(self) -> Path:
        """Frozen snapshot of the original Google Sheet."""
        return self.root / "data" / "legacy"

    @property
    def build(self) -> Path:
        return self.root / "build"

    @property
    def database(self) -> Path:
        """Working copy, built from data/db (never committed)."""
        return self.build / "termquake.db"

    @property
    def site_public(self) -> Path:
        return self.root / "site" / "public"


@dataclass(frozen=True)
class Config:
    languages: list[str]  # language codes, in display order
    sheet_id: str
    tabs: dict[str, str]  # sheet tab name -> snapshot file stem
    columns: dict[str, str]  # English language name in the sheet header -> code
    domains: dict[str, str]  # sheet "Domain" value -> domain code

    @property
    def sheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"


def load_config(path: Path | None = None) -> Config:
    path = path or REPO_ROOT / "termquake.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    sheet = raw["sheet"]
    return Config(
        languages=list(raw["languages"]),
        sheet_id=sheet["id"],
        tabs=dict(sheet["tabs"]),
        columns=dict(sheet["columns"]),
        domains=dict(sheet["domains"]),
    )

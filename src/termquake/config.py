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
        return self.root / "db"

    @property
    def raw(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def export(self) -> Path:
        return self.root / "data" / "export"

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
    sheet_id: str
    tabs: dict[str, str]  # sheet tab name -> raw file stem
    languages: list[str]  # published language codes, in display order
    pivot: str
    columns: dict[str, str]  # English language name -> code
    domains: dict[str, str]  # domain label -> domain code
    phrase_labels: list[str]

    @property
    def export_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=xlsx"

    @property
    def sheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"


def load_config(path: Path | None = None) -> Config:
    path = path or REPO_ROOT / "termquake.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    languages = list(raw["publish"]["languages"])
    pivot = raw["publish"].get("pivot", languages[0])
    if pivot not in languages:
        raise ValueError(f"publish.pivot '{pivot}' must be one of publish.languages")
    codes = set(raw["columns"].values())
    missing = [code for code in languages if code not in codes]
    if missing:
        raise ValueError(f"publish.languages {missing} have no column mapping in [columns]")

    return Config(
        sheet_id=raw["sheet"]["id"],
        tabs=dict(raw["sheet"]["tabs"]),
        languages=languages,
        pivot=pivot,
        columns=dict(raw["columns"]),
        domains=dict(raw["domains"]),
        phrase_labels=list(raw["entry_types"]["phrase_labels"]),
    )

"""Download the Google Sheet and mirror selected tabs into data/raw/*.csv.

The sheet is public ("anyone with the link can view"), so the plain xlsx
export works without an API key: no secrets to store or leak. One request
returns every tab at once, which keeps tab IDs (gid) out of the config.

The CSV snapshot is the hand-off point between the network (unreliable,
changes any time) and the build (deterministic, testable offline). It is
committed to git, so every change anyone makes in the sheet becomes a
readable, dated diff in the repository history.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import re
import urllib.request
from pathlib import Path

from openpyxl import load_workbook

from .config import Config

USER_AGENT = "TermQuake-sync/1.0 (+https://github.com/ysfztpp/termquake)"


def download_xlsx(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (fixed https URL)
        data = response.read()
    if not data.startswith(b"PK"):
        raise RuntimeError(
            "Download is not an xlsx file. Is the sheet still shared as "
            "'anyone with the link can view'?"
        )
    return data


def _cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    return str(value)


_XLSX_FORBIDDEN = re.compile(r"[\[\]:*?/\\\s]")


def _tab_key(name: str) -> str:
    return _XLSX_FORBIDDEN.sub("", name).casefold()


def resolve_tab(wanted: str, available: list[str]) -> str:
    """Find a Google Sheets tab inside the xlsx export.

    xlsx tab names cannot contain / \\ ? * [ ] : and are cut at 31 characters,
    so Google renames e.g. "All Terms and Expressions /Terimler ve İfadeler"
    on export. Match exactly first, then ignoring forbidden characters and
    allowing truncation.
    """
    if wanted in available:
        return wanted
    key = _tab_key(wanted)
    hits = [name for name in available if (k := _tab_key(name)) and key.startswith(k)]
    if len(hits) == 1:
        return hits[0]
    raise RuntimeError(
        f"Tab {wanted!r} not found (candidates: {hits or 'none'}). Available tabs: {available}. "
        "Update [sheet.tabs] in termquake.toml if a tab was renamed."
    )


def workbook_to_csvs(xlsx: bytes, tabs: dict[str, str]) -> dict[str, str]:
    """Return {file_stem: csv_text} for the configured tabs."""
    wb = load_workbook(io.BytesIO(xlsx), read_only=True, data_only=True)
    out: dict[str, str] = {}
    try:
        for tab, stem in tabs.items():
            sheet = wb[resolve_tab(tab, wb.sheetnames)]
            rows = [[_cell_to_text(v) for v in row] for row in sheet.iter_rows(values_only=True)]
            out[stem] = _rows_to_csv(rows)
    finally:
        wb.close()
    return out


def _rows_to_csv(rows: list[list[str]]) -> str:
    # Trim trailing empty rows and columns so the snapshot only changes when content does.
    while rows and not any(cell.strip() for cell in rows[-1]):
        rows.pop()
    width = 0
    for row in rows:
        for i in range(len(row) - 1, -1, -1):
            if row[i].strip():
                width = max(width, i + 1)
                break
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        writer.writerow((row + [""] * width)[:width])
    return buf.getvalue()


def sync(config: Config, raw_dir: Path) -> list[str]:
    """Fetch the sheet and write snapshots. Returns the list of files that changed."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    csvs = workbook_to_csvs(download_xlsx(config.export_url), config.tabs)
    changed: list[str] = []
    for stem, text in csvs.items():
        path = raw_dir / f"{stem}.csv"
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != text:
            path.write_text(text, encoding="utf-8")
            changed.append(path.name)
    return changed


def snapshot_digest(raw_dir: Path) -> str:
    """Stable fingerprint of the raw snapshot, used as the data version."""
    h = hashlib.sha256()
    for path in sorted(raw_dir.glob("*.csv")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]

"""Read every workbook in a folder into one long table."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "child_id", "sex", "birth_date", "school_year", "group", "assessment_date",
    "rater", "vocabulary", "phonological_awareness", "letter_knowledge",
]
WAVE_SHEETS = ("pre", "post")


class WorkbookStructureError(ValueError):
    """Raised when a workbook does not have the expected sheets or columns."""


def read_metadata(path: Path) -> dict[str, str]:
    meta = pd.read_excel(path, sheet_name="metadata")
    return dict(zip(meta["field"], meta["value"].astype(str)))


def read_workbook(path: Path) -> pd.DataFrame:
    sheets = pd.ExcelFile(path).sheet_names
    missing = [s for s in ("metadata", *WAVE_SHEETS) if s not in sheets]
    if missing:
        raise WorkbookStructureError(f"{path.name}: missing sheets {missing}")

    meta = read_metadata(path)
    frames = []
    for wave in WAVE_SHEETS:
        df = pd.read_excel(path, sheet_name=wave)
        absent = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if absent:
            raise WorkbookStructureError(f"{path.name}/{wave}: missing columns {absent}")
        df = df[EXPECTED_COLUMNS].copy()
        df["wave"] = wave
        df["school_id"] = meta.get("school_id", path.stem)
        df["region"] = meta.get("region")
        df["source_file"] = path.name
        df["source_row"] = df.index + 2  # Excel row number (header is row 1)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def read_folder(folder: Path) -> tuple[pd.DataFrame, list[str]]:
    """Return the stacked data and a list of files that could not be read."""
    frames, problems = [], []
    for path in sorted(Path(folder).glob("*.xlsx")):
        try:
            frames.append(read_workbook(path))
        except WorkbookStructureError as exc:
            problems.append(str(exc))
    if not frames:
        raise FileNotFoundError(f"No readable .xlsx files in {folder}")
    data = pd.concat(frames, ignore_index=True)
    for col in ("birth_date", "assessment_date"):
        data[col] = pd.to_datetime(data[col], errors="coerce")
    return data, problems

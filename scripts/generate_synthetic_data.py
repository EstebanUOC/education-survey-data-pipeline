"""Generate synthetic school workbooks that mimic the structure of the
assessment files used in a multi-school kindergarten study.

No real data is used. Some errors are injected on purpose (out-of-range
scores, duplicated IDs, ages that do not match the school year, missing
values) so that the validation step has something to find.

Usage: python scripts/generate_synthetic_data.py --out data/raw --schools 12 --seed 42
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SCHOOL_YEARS = {"P3": 3, "P4": 4, "P5": 5}
WAVES = {"pre": date(2023, 10, 15), "post": date(2024, 5, 20)}


def make_school(school_id: str, rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    n = int(rng.integers(15, 30))
    group = rng.choice(["intervention", "control"])
    school_year = rng.choice(list(SCHOOL_YEARS))
    base_year = WAVES["pre"].year - SCHOOL_YEARS[school_year]
    births = [date(base_year, 1, 1) + timedelta(days=int(d)) for d in rng.integers(0, 365, n)]
    ids = [f"{school_id}-{i:03d}" for i in range(1, n + 1)]
    ability = rng.normal(0, 1, n)

    sheets = {}
    for wave, adate in WAVES.items():
        gain = 0.0 if wave == "pre" else (0.9 if group == "intervention" else 0.5)
        df = pd.DataFrame({
            "child_id": ids,
            "sex": rng.choice(["F", "M"], n),
            "birth_date": births,
            "school_year": school_year,
            "group": group,
            "assessment_date": adate,
            "rater": rng.choice(["R1", "R2", "R3"], n),
            "vocabulary": np.clip(np.round(20 + 5 * (ability + gain) + rng.normal(0, 2, n)), 0, 40),
            "phonological_awareness": np.clip(np.round(12 + 4 * (ability + gain) + rng.normal(0, 2, n)), 0, 30),
            "letter_knowledge": np.clip(np.round(10 + 5 * (ability + gain) + rng.normal(0, 2, n)), 0, 27),
        })
        sheets[wave] = df

    # Inject realistic data-entry errors
    pre, post = sheets["pre"], sheets["post"]
    if rng.random() < 0.5:
        pre.loc[rng.integers(0, n), "vocabulary"] = 99          # typo / out of range
    if rng.random() < 0.4:
        post.loc[rng.integers(0, n), "letter_knowledge"] = np.nan  # missing value
    if rng.random() < 0.3:
        post = pd.concat([post, post.iloc[[0]]], ignore_index=True)  # duplicated row
    if rng.random() < 0.3:
        pre.loc[rng.integers(0, n), "birth_date"] = date(base_year - 2, 6, 1)  # wrong cohort
    sheets["post"] = post
    return sheets


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--schools", type=int, default=12)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for s in range(1, args.schools + 1):
        school_id = f"S{s:02d}"
        sheets = make_school(school_id, rng)
        with pd.ExcelWriter(out / f"school_{school_id}.xlsx") as xw:
            pd.DataFrame({"field": ["school_id", "region"],
                          "value": [school_id, rng.choice(["North", "South", "East", "West"])]}
                         ).to_excel(xw, sheet_name="metadata", index=False)
            for wave, df in sheets.items():
                df.to_excel(xw, sheet_name=wave, index=False)
    print(f"Wrote {args.schools} workbooks to {out}")


if __name__ == "__main__":
    main()

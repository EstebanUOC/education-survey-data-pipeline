"""Build the consolidated dataset and a per-school quality-control summary."""
from __future__ import annotations

import pandas as pd

SCORES = ["vocabulary", "phonological_awareness", "letter_knowledge"]


def consolidate(data: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per child and wave; set values that fail an error rule to missing.

    Rows are never silently dropped: every change is traceable in the issues log.
    """
    clean = data.drop_duplicates(subset=["school_id", "wave", "child_id"], keep="first").copy()
    errors = issues[(issues["severity"] == "error") & issues["column"].isin(SCORES)]
    for _, issue in errors.iterrows():
        mask = (clean["school_id"] == issue["school_id"]) & (clean["wave"] == issue["wave"]) \
            & (clean["child_id"] == issue["child_id"])
        clean.loc[mask, issue["column"]] = pd.NA
    return clean.sort_values(["school_id", "child_id", "wave"]).reset_index(drop=True)


def qc_summary(data: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    rows = data.groupby("school_id").size().rename("records")
    if issues.empty:
        summary = rows.to_frame().assign(errors=0, warnings=0)
    else:
        counts = issues.pivot_table(index="school_id", columns="severity",
                                    values="rule_id", aggfunc="count", fill_value=0)
        summary = rows.to_frame().join(counts).fillna(0)
        summary = summary.rename(columns={"error": "errors", "warning": "warnings"})
        for c in ("errors", "warnings"):
            if c not in summary:
                summary[c] = 0
    summary["status"] = summary["errors"].map(lambda e: "needs follow-up" if e else "passed")
    return summary[["records", "errors", "warnings", "status"]].astype(
        {"errors": int, "warnings": int}).reset_index()

"""Apply the validation rules defined in config/validation_rules.csv.

Rules live in a CSV file so that methodologists can read and change them
without touching the code. Each rule returns the rows that fail it.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def add_age(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    days = (data["assessment_date"] - data["birth_date"]).dt.days
    data["age_months"] = (days / 30.4375).round(1)
    return data


def _failing_rows(data: pd.DataFrame, rule: pd.Series, cohorts: pd.DataFrame) -> pd.Series:
    col, check = rule["column"], rule["check"]
    if check == "not_missing":
        return data[col].isna()
    if check == "range":
        values = data[col]
        return values.notna() & ((values < rule["min"]) | (values > rule["max"]))
    if check == "unique_per_wave":
        return data.duplicated(subset=["school_id", "wave", col], keep=False)
    if check == "after_birth":
        return data["assessment_date"] <= data["birth_date"]
    if check == "cohort_match":
        bounds = data[["school_year"]].merge(cohorts, on="school_year", how="left")
        age = data[col].to_numpy()
        return pd.Series((age < bounds["min_age_months"].to_numpy())
                         | (age > bounds["max_age_months"].to_numpy()), index=data.index)
    raise ValueError(f"Unknown check '{check}' in rule {rule['rule_id']}")


def validate(data: pd.DataFrame, rules: pd.DataFrame, cohorts: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (record, rule) failure."""
    issues = []
    for _, rule in rules.iterrows():
        mask = _failing_rows(data, rule, cohorts)
        if mask.any():
            failed = data.loc[mask, ["school_id", "wave", "child_id", "source_file", "source_row"]].copy()
            failed["rule_id"] = rule["rule_id"]
            failed["severity"] = rule["severity"]
            failed["column"] = rule["column"]
            failed["value"] = data.loc[mask, rule["column"]].astype(str)
            failed["description"] = rule["description"]
            issues.append(failed)
    cols = ["school_id", "wave", "child_id", "source_file", "source_row",
            "rule_id", "severity", "column", "value", "description"]
    return pd.concat(issues, ignore_index=True) if issues else pd.DataFrame(columns=cols)


def load_config(config_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = pd.read_csv(Path(config_dir) / "validation_rules.csv")
    cohorts = pd.read_csv(Path(config_dir) / "cohorts.csv")
    return rules, cohorts

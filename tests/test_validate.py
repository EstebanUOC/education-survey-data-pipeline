from pathlib import Path

import pandas as pd

from pipeline.consolidate import consolidate, qc_summary
from pipeline.validate import add_age, load_config, validate

CONFIG = Path(__file__).resolve().parents[1] / "config"


def make_rows(**overrides):
    base = {
        "school_id": "S01", "wave": "pre", "child_id": "S01-001",
        "birth_date": pd.Timestamp("2018-03-01"), "assessment_date": pd.Timestamp("2023-10-15"),
        "school_year": "P5", "group": "control", "vocabulary": 20.0,
        "phonological_awareness": 10.0, "letter_knowledge": 12.0,
        "source_file": "school_S01.xlsx", "source_row": 2,
    }
    base.update(overrides)
    return base


def run(rows):
    rules, cohorts = load_config(CONFIG)
    data = add_age(pd.DataFrame(rows))
    return data, validate(data, rules, cohorts)


def test_clean_record_passes():
    _, issues = run([make_rows()])
    assert issues.empty


def test_out_of_range_score_is_an_error():
    _, issues = run([make_rows(vocabulary=99.0)])
    assert set(issues["rule_id"]) == {"R06"}
    assert (issues["severity"] == "error").all()


def test_duplicate_child_in_same_wave_is_flagged():
    _, issues = run([make_rows(), make_rows()])
    assert (issues["rule_id"] == "R02").sum() == 2


def test_age_inconsistent_with_school_year_is_a_warning():
    _, issues = run([make_rows(birth_date=pd.Timestamp("2016-01-01"))])
    assert "R05" in set(issues["rule_id"])


def test_consolidate_removes_duplicates_and_bad_values():
    data, issues = run([make_rows(vocabulary=99.0), make_rows(vocabulary=99.0)])
    clean = consolidate(data, issues)
    assert len(clean) == 1
    assert pd.isna(clean.loc[0, "vocabulary"])
    summary = qc_summary(data, issues)
    assert summary.loc[0, "status"] == "needs follow-up"

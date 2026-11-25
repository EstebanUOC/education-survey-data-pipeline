"""Command-line entry point: python -m pipeline --input data/raw --output outputs"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .consolidate import consolidate, qc_summary
from .read import read_folder
from .report import write_outputs
from .validate import add_age, load_config, validate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/raw", type=Path)
    ap.add_argument("--config", default="config", type=Path)
    ap.add_argument("--output", default="outputs", type=Path)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("pipeline")

    data, problems = read_folder(args.input)
    log.info("Read %d records from %d schools", len(data), data["school_id"].nunique())
    for p in problems:
        log.warning("Skipped: %s", p)

    rules, cohorts = load_config(args.config)
    data = add_age(data)
    issues = validate(data, rules, cohorts)
    log.info("Validation: %d errors, %d warnings",
             (issues["severity"] == "error").sum(), (issues["severity"] == "warning").sum())

    clean = consolidate(data, issues)
    summary = qc_summary(data, issues)
    write_outputs(clean, issues, summary, problems, args.output)
    log.info("Outputs written to %s", args.output)


if __name__ == "__main__":
    main()

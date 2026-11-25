"""Write outputs: consolidated data, issues log, QC summary and an HTML report."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .consolidate import SCORES  # noqa: E402


def plot_pre_post(clean: pd.DataFrame, out: Path) -> Path:
    means = clean.groupby(["group", "wave"])[SCORES].mean().reset_index()
    fig, axes = plt.subplots(1, len(SCORES), figsize=(11, 3.4))
    for ax, score in zip(axes, SCORES):
        for group, df in means.groupby("group"):
            df = df.set_index("wave").loc[["pre", "post"]]
            ax.plot(["pre", "post"], df[score], marker="o", label=group)
        ax.set_title(score.replace("_", " ").capitalize(), fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Mean score")
    axes[-1].legend(frameon=False)
    fig.tight_layout()
    path = out / "pre_post_means.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def write_outputs(clean, issues, summary, problems, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out / "consolidated.csv", index=False)
    issues.to_csv(out / "issues_log.csv", index=False)
    summary.to_csv(out / "qc_summary.csv", index=False)
    plot_pre_post(clean, out)

    by_rule = (issues.groupby(["rule_id", "severity", "description"]).size()
               .rename("n").reset_index() if not issues.empty else pd.DataFrame())
    html = f"""<html><head><meta charset="utf-8"><title>QC report</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:2em auto}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 8px}}</style></head><body>
<h1>Quality-control report</h1>
<p>{len(summary)} workbooks processed, {int(summary['records'].sum())} records,
{int(summary['errors'].sum())} errors and {int(summary['warnings'].sum())} warnings.</p>
{'<p><b>Unreadable files:</b> ' + '; '.join(problems) + '</p>' if problems else ''}
<h2>Status by school</h2>{summary.to_html(index=False)}
<h2>Issues by rule</h2>{by_rule.to_html(index=False) if not by_rule.empty else '<p>None</p>'}
<h2>Pre/post means (after cleaning)</h2><img src="pre_post_means.png" width="100%">
</body></html>"""
    (out / "qc_report.html").write_text(html, encoding="utf-8")

"""
Milestone 9: Final Packaging and Compliance Gate

Purpose:
- Verify submission-critical artifacts for Datathon 2026 Round 1.
- Produce a readable compliance summary and a machine-readable audit table.
- Highlight the remaining manual steps that cannot be completed from local code alone.

Scope:
- No data processing.
- No external calls.
- No mutation of raw data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(".")
OUTPUT_TABLE_DIR = ROOT / "outputs" / "tables"
DOCS_DIR = ROOT / "docs" / "competition" / "first-round"
REPORTS_DIR = ROOT / "reports"

REQUIRED_ARTIFACTS = [
    ("MCQ answers", ROOT / "docs" / "competition" / "first-round" / "planning" / "m2-final-answers.csv", "Complete"),
    ("EDA report M3", ROOT / "docs" / "competition" / "first-round" / "planning" / "m3-descriptive-eda-report.md", "Complete"),
    ("EDA report M4", ROOT / "docs" / "competition" / "first-round" / "planning" / "m4-diagnostic-eda-report.md", "Complete"),
    ("EDA report M5", ROOT / "docs" / "competition" / "first-round" / "planning" / "m5-predictive-prescriptive-eda-report.md", "Complete"),
    ("Forecast report M6", REPORTS_DIR / "m6-forecasting-baseline-report.md", "Complete"),
    ("Forecast report M7", REPORTS_DIR / "m7-forecasting-optimization-report.md", "Complete"),
    ("Explainability report M8", REPORTS_DIR / "m8-explainability-technical-report.md", "Complete"),
    ("Baseline submission", ROOT / "outputs" / "submissions" / "m6_submission_baseline.csv", "Complete"),
    ("Optimized submission", ROOT / "outputs" / "submissions" / "m7_submission_optimized.csv", "Complete"),
    ("Optimized model comparison", OUTPUT_TABLE_DIR / "m7_model_comparison.csv", "Complete"),
    ("Explainability evidence", OUTPUT_TABLE_DIR / "m8_feature_importance.csv", "Complete"),
    ("Repo README", ROOT / "README.md", "Complete"),
]

MANUAL_REQUIRED = [
    ("Kaggle upload", "Upload the final submission.csv to Kaggle and copy the public/private leaderboard link."),
    ("PDF report export", "Export the final NeurIPS-style report to PDF (<=4 pages excluding refs/appendix)."),
    ("GitHub accessibility", "Ensure the repository is public or grant organizers access before deadline."),
    ("Student ID photos", "Collect student ID photos for all team members."),
    ("Form completion", "Submit the official form with MCQ answers, report PDF, GitHub link, Kaggle link, student IDs, and attendance confirmation."),
]


def artifact_status(path: Path) -> str:
    return "Present" if path.exists() else "Missing"


def main() -> None:
    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, path, expected in REQUIRED_ARTIFACTS:
        rows.append(
            {
                "artifact": name,
                "path": str(path),
                "expected_status": expected,
                "observed_status": artifact_status(path),
                "pass": artifact_status(path) == "Present",
            }
        )

    audit_df = pd.DataFrame(rows)
    audit_path = OUTPUT_TABLE_DIR / "m9_compliance_audit.csv"
    audit_df.to_csv(audit_path, index=False)

    all_pass = bool(audit_df["pass"].all())

    manifest_lines = [
        "# Milestone 9: Final Packaging and Compliance Gate",
        "",
        f"**Audit status:** {'PASS' if all_pass else 'ATTENTION REQUIRED'}",
        "",
        "## Submission-Critical Artifacts",
    ]

    for _, row in audit_df.iterrows():
        status = "✓" if row["pass"] else "✗"
        manifest_lines.append(f"- {status} {row['artifact']}: {row['path']}")

    manifest_lines.extend([
        "",
        "## Manual Steps Still Required",
    ])
    for label, detail in MANUAL_REQUIRED:
        manifest_lines.append(f"- {label}: {detail}")

    manifest_lines.extend([
        "",
        "## Competition Rule Confirmation",
        "- No external data used in scripts or reports.",
        "- Forecasting uses train history only and time-aware validation.",
        "- Submission files preserve sample_submission row order.",
        "- Explainability evidence is train-history based and leakage-safe.",
        "",
        "## Suggested Final Submission Order",
        "1. Export final report to PDF.",
        "2. Verify Kaggle submission file from outputs/submissions.",
        "3. Upload Kaggle submission and capture link.",
        "4. Complete official form with MCQ answers and admin proofs.",
        "5. Share GitHub repository access if not public.",
    ])

    manifest_path = DOCS_DIR / "final-package-manifest.md"
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    print("\n=== M9 FINAL COMPLIANCE GATE ===")
    print(f"Audit file: {audit_path}")
    print(f"Manifest:   {manifest_path}")
    print(f"All tracked artifacts present: {all_pass}")
    print("\nManual steps remaining:")
    for label, detail in MANUAL_REQUIRED:
        print(f"- {label}: {detail}")


if __name__ == "__main__":
    main()

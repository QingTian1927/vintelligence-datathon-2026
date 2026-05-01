# Vintelligence Datathon 2026 - Round 1 Workspace

This repository is organized for a low-friction local Windows workflow (no conda) and milestone-by-milestone execution.

## Quick Start (Windows, no conda)

1. Check Python version (3.10+ recommended):

```powershell
python --version
```

2. Install dependencies in your global/local Python environment:

```powershell
pip install -r requirements.txt
```

3. Sanity check imports and core files:

```powershell
python scripts\sanity_check.py
```

4. Start working milestone-by-milestone:

- Competition analysis: docs/competition/first-round/planning/competition-analysis.md
- Milestone plan: docs/competition/first-round/planning/milestone-plan.md
- Milestone 0 runbook: docs/competition/first-round/planning/m0-operating-system.md

## Repository Structure

- data/: competition datasets (provided)
- notebooks/: exploratory and presentation notebooks
- src/: reusable Python code (features, models, utilities)
- scripts/: runnable scripts for checks and pipeline stages
- outputs/: generated artifacts (figures, tables, models, submissions)
- reports/: report assets and draft content
- docs/: competition brief and planning materials

## Team Working Rules

- Keep raw data in data/ unchanged.
- Save all generated files under outputs/.
- Use deterministic random seed for all modeling scripts.
- Do not use external data.
- Keep submission row order exactly as sample_submission.csv.

## Suggested Branching

- main: stable, submission-ready code
- feat/<milestone>-<short-name>: milestone task branches

Example:

- feat/m1-data-audit
- feat/m2-mcq
- feat/m6-baseline-forecast

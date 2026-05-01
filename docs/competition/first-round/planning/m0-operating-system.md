# Milestone 0 Operating System

## Objective
Create a low-friction, reproducible, team-ready project foundation before modeling and analysis.

## Scope Completed in Milestone 0
- Repository structure for code, notebooks, outputs, and report assets
- Single-command dependency setup (no conda)
- Sanity check script for data and packages
- Working agreements for contributors
- Compliance guardrails tied to competition rules

## Environment Policy
- OS target: Windows local setup
- Python: 3.10+ recommended
- No conda required
- Install command:

```powershell
pip install -r requirements.txt
```

## Run Order for New Teammates
1. Clone repository.
2. Run `pip install -r requirements.txt`.
3. Run `python scripts\\sanity_check.py`.
4. Read planning docs in `docs/competition/first-round/planning/`.
5. Start current active milestone branch.

## Folder Responsibilities
- `data/`: read-only competition data
- `notebooks/`: ad hoc exploration and presentation notebooks
- `src/`: reusable logic for features/models/utilities
- `scripts/`: repeatable commands and checks
- `outputs/`: generated artifacts only
- `reports/assets/`: figures/tables used in report

## Team Conventions
- Branch naming: `feat/m<id>-<task>`
- Script naming: verb-based, e.g., `build_features.py`, `train_baseline.py`
- Notebook naming: `m<id>_<topic>_v<xx>.ipynb`
- Random seed default: 42
- Timezone/date handling: treat source dates as date-only unless specified

## Compliance Guardrails
- No external data usage.
- No leakage from hidden test targets.
- Keep submission row order identical to `sample_submission.csv`.
- Ensure all final results are reproducible from repository code.

## Exit Criteria for Milestone 0
- Teammate can set up and pass sanity check in one pass.
- Core structure exists for all future milestones.
- Rules/checklists are documented and discoverable.

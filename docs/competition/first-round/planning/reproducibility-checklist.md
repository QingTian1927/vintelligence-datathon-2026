# Reproducibility Checklist

Use this checklist before locking any milestone output.

## Code and Data Integrity
- [ ] Raw files in `data/` are unchanged.
- [ ] No external datasets are referenced.
- [ ] Script/notebook clearly states input files and output files.

## Determinism and Validation
- [ ] Random seed is fixed (default 42) in all model-related code.
- [ ] Time-based validation is used for forecasting tasks.
- [ ] No leakage features from future dates are used.

## Artifact Tracking
- [ ] Generated artifacts are saved under `outputs/`.
- [ ] Final report figures/tables are copied into `reports/assets/`.
- [ ] Model version and feature set used are documented.

## Execution Hygiene
- [ ] Commands required to reproduce are listed in milestone notes.
- [ ] `python scripts/sanity_check.py` passes.
- [ ] Team member can rerun key pipeline steps without manual patching.

## Submission Safety
- [ ] Submission follows exact schema of `sample_submission.csv`.
- [ ] Submission row order matches sample exactly.
- [ ] Pre-submission script or manual verification has been performed.

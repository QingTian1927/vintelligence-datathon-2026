# Datathon 2026 Round 1 Submission Package

Prepared from the finalized repository state on 2026-05-01.

## 1) What the email requires
The official email asks for:
- MCQ answers
- Report PDF
- GitHub repository link
- Kaggle submission link
- Student ID photos for all team members
- Attendance confirmation checkbox for at least one member at the final round in Hanoi

## 2) Repo artifacts ready now
### MCQ
- Final answers: `docs/competition/first-round/planning/m2-final-answers.csv`

### Part 2 reports
- Descriptive EDA: `docs/competition/first-round/planning/m3-descriptive-eda-report.md`
- Diagnostic EDA: `docs/competition/first-round/planning/m4-diagnostic-eda-report.md`
- Predictive & Prescriptive EDA: `docs/competition/first-round/planning/m5-predictive-prescriptive-eda-report.md`

### Part 3 reports
- Baseline forecasting: `reports/m6-forecasting-baseline-report.md`
- Optimized forecasting: `reports/m7-forecasting-optimization-report.md`
- Explainability: `reports/m8-explainability-technical-report.md`

### Submission files
- Baseline submission: `outputs/submissions/m6_submission_baseline.csv`
- Optimized submission: `outputs/submissions/m7_submission_optimized.csv`
- Final competition-named submission: `outputs/submissions/submission.csv`
- Stronger dual-target builder: `scripts/m10_stronger_submission.py`

### Evidence and audit files
- Final compliance audit: `outputs/tables/m9_compliance_audit.csv`
- Final packaging manifest: `docs/competition/first-round/final-package-manifest.md`
- Explainability evidence: `outputs/tables/m8_feature_importance.csv`
- Forecast comparison: `outputs/tables/m7_model_comparison.csv`

## 3) Manual items still required before upload
- Export the final report to PDF in NeurIPS format, max 4 pages excluding references and appendix.
- Upload `outputs/submissions/submission.csv` to Kaggle.
- Copy the Kaggle submission link.
- Confirm GitHub repository access is public or shared with organizers.
- Gather student ID photos for all team members.
- Complete the official form with MCQ answers, report PDF, GitHub link, Kaggle link, IDs, and attendance confirmation.

## 4) Submission order recommended by the email
1. Finalize report PDF.
2. Upload `submission.csv` to Kaggle.
3. Verify the Kaggle link.
4. Check GitHub access.
5. Attach student ID photos.
6. Submit the official form.

## 5) Competition rule reminders
- No external data.
- No leakage from hidden test Revenue/COGS into modeling features.
- Submission row order must match `sample_submission.csv` exactly.
- Code and outputs are reproducible from the repository.

## 6) Current best model choice
- Submission winner: dual-target LightGBM blend with `alpha=0.90`
- Rationale: predicts both `Revenue` and `COGS`, and the holdout average MAE is lower than the earlier Revenue-only submission path
- Explainability: strongest drivers remain short-term lags plus seasonal structure

## 7) Final note
The repository is ready for packaging. The only remaining work is the external submission workflow required by the competition portal and Kaggle.

# Datathon 2026 Round 1: Milestone Plan

This plan maps directly to competition requirements and scoring. Work strictly one milestone at a time.

## Milestone 0: Project Operating System
Objective:
- Establish reproducible structure, run rules, naming conventions, and master checklist.

Deliverables:
- Folder layout for data, notebooks, scripts, outputs, report assets
- Reproducibility guide (seed policy, run order)
- Submission checklist template

Definition of Done:
- Another teammate can reproduce core outputs end-to-end from instructions.

## Milestone 1: Data Audit and Join Validation
Objective:
- Confirm schema quality and relational assumptions before any scoring work.

Deliverables:
- Data quality report (nulls, duplicates, ranges, type checks)
- Join/cardinality validation notes
- Leakage watchlist

Definition of Done:
- Critical data risks identified with explicit handling rules.

## Milestone 2: MCQ Automation (Part 1)
Objective:
- Produce reproducible answers for all 10 MCQ questions.

Deliverables:
- Deterministic computation script/notebook per question
- Final answer sheet with supporting numeric evidence

Definition of Done:
- Each answer is traceable and reproducible from raw data.

## Milestone 3: EDA Descriptive Layer (Part 2)
Objective:
- Build high-quality descriptive insights and visual baseline.

Deliverables:
- Core trend/distribution/segmentation charts
- Descriptive findings summary with metrics

Definition of Done:
- Clear, accurate answer to "What happened?"

## Milestone 4: EDA Diagnostic Layer (Part 2)
Objective:
- Explain why patterns occurred and identify key drivers.

Deliverables:
- Segment/channel/product/root-cause analyses
- Evidence-backed hypotheses and anomaly notes

Definition of Done:
- Clear, data-backed answer to "Why did it happen?"

## Milestone 5: EDA Predictive + Prescriptive Layer (Part 2)
Objective:
- Convert insights into forward-looking and actionable recommendations.

Deliverables:
- Scenario/projection views
- Prioritized recommendations with quantified trade-offs

Definition of Done:
- Strong answer to "What is likely to happen?" and "What should we do?"

## Milestone 6: Forecasting Baseline Pipeline (Part 3)
Objective:
- Build a leak-safe, time-aware baseline forecast pipeline.

Deliverables:
- Time-based validation framework
- Baseline model metrics (MAE, RMSE, R2)
- First valid Kaggle submission

Definition of Done:
- Stable benchmark with trustworthy offline validation.

## Milestone 7: Forecasting Optimization and Ensembling (Part 3)
Objective:
- Improve model performance for leaderboard competitiveness.

Deliverables:
- Enhanced feature engineering
- Tuned model candidates and comparison table
- Ensemble/blend strategy and final model choice

Definition of Done:
- Measurable lift versus baseline with documented selection rationale.

## Milestone 8: Explainability and Technical Report Content (Part 3)
Objective:
- Secure technical-report points through clear model interpretation and method transparency.

Deliverables:
- Feature importance/SHAP analysis
- Leakage prevention and CV strategy documentation
- Business-language model interpretation

Definition of Done:
- Judges can understand model behavior, trust controls, and business relevance.

## Milestone 9: Final Packaging and Compliance Gate
Objective:
- Ensure complete, valid, on-time submission package.

Deliverables:
- Report PDF, repo, Kaggle link, MCQ answers, required admin proofs
- Final compliance check against all rules

Definition of Done:
- Full package submitted without missing items or format violations.

## Execution Rule (One Milestone at a Time)
For each milestone, run this sequence:

1. Plan
2. Implement
3. Validate
4. Summarize evidence
5. Lock output

Do not start the next milestone until current Definition of Done is met.

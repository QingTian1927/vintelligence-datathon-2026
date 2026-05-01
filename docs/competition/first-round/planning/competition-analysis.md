# Datathon 2026 Round 1: Competition Analysis

## 1) Competition Structure and Scoring
Total score is 100 points, split across three parts:

- Part 1: MCQ (20 points)
- Part 2: EDA + Visualization + Business Analysis (60 points)
- Part 3: Revenue Forecasting on Kaggle (20 points)

Key implication: leaderboard performance alone cannot win the round. The largest score weight is Part 2.

## 2) Official Deliverables
A complete submission package requires all of the following:

- MCQ answers (10 questions)
- Report PDF (NeurIPS template, max 4 pages excluding references and appendix)
- Public/reviewable GitHub repository with reproducible code
- Kaggle submission link
- Student ID photos for all team members
- Confirmation that at least 1 member can attend the in-person final (23/05/2026, VinUni Hanoi)

Hard deadline: 23:59 on 01/05/2026.

## 3) Forecasting Task Definition (Part 3)
Target task:

- Forecast daily `Revenue` for the hidden test period 01/01/2023 to 01/07/2024
- Train period is 04/07/2012 to 31/12/2022

Evaluation metrics used jointly:

- MAE (lower is better)
- RMSE (lower is better)
- R2 (higher is better)

Submission format constraints:

- Keep exact row order as `sample_submission.csv`
- Do not shuffle/sort rows

## 4) Data Landscape
The dataset spans 15 CSV files in 4 layers:

- Master: products, customers, promotions, geography
- Transaction: orders, order_items, payments, shipments, returns, reviews
- Analytical: sales (+ sample submission format)
- Operational: inventory (monthly), web_traffic (daily)

Analysis opportunity:

- Rich relational data enables exogenous features for forecasting (promotion, traffic, inventory, returns, product mix, channel behavior).

## 5) Rules and Disqualification Risks
Critical constraints from the brief:

- No external data
- Reproducible code required
- Explainability required in report (feature importance/SHAP/PDP or equivalent)
- Do not leak hidden test target information into training/features

Part 3 can be fully disqualified if constraints are violated (e.g., leakage, external data, irreproducible pipeline).

## 6) EDA Rubric Implications (Part 2, 60 points)
Part 2 is judged on:

- Visualization quality (15)
- Analytical depth across 4 levels (25): Descriptive -> Diagnostic -> Predictive -> Prescriptive
- Business insight/actionability (15)
- Creativity/storytelling (5)

High-score requirement:

- Consistent prescriptive analysis backed by quantified trade-offs and actionable recommendations.

## 7) Strategic Takeaways
- Optimize for total score, not only Kaggle rank.
- Build one integrated narrative linking data exploration, business recommendations, and forecasting logic.
- Prioritize leakage-safe, time-aware validation for forecasting.
- Treat report clarity and reproducibility as first-class deliverables.

## 8) Practical Risk Register
- Time compression risk (few days left before deadline)
- Leakage risk from multi-table joins and temporal features
- Reproducibility risk if notebook-only workflow is not standardized
- Scope creep risk in EDA (too many plots, low narrative quality)
- Administrative risk (incomplete submission package)

## 9) Recommended Operating Principles
- Work milestone-by-milestone with acceptance criteria.
- Lock each milestone before moving to the next.
- Keep a compliance checklist updated continuously.
- Version every model run and submission artifact.
- Draft report sections in parallel with analysis to avoid last-day bottlenecks.

# Milestone 7: Forecasting Optimization and Ensembling Report

Execution date: 2026-04-27

## Objective
Improve forecasting quality over Milestone 6 baseline through stronger feature engineering, parameter tuning, and blend selection, while staying fully compliant with Part 3 constraints.

## Rule Compliance Checklist
- Data source: only provided competition files.
- Training window: 2012-07-04 to 2022-12-31 from sales.csv.
- Forecast horizon: 2023-01-01 to 2024-07-01 (sample_submission order preserved).
- No use of hidden test Revenue or hidden test COGS as model features.
- Time-aware validation (expanding-window folds, no random split).
- Reproducibility: fixed random seed = 42.

## Optimization Design
Compared three candidates under time-aware folds:
1. seasonal_year_lag365
- Strong seasonal baseline using lag-365 recursive prediction.

2. gbr_recursive
- GradientBoostingRegressor on enhanced features:
  - Lag features: 1, 2, 3, 7, 14, 21, 28, 56, 84, 168, 365
  - Rolling stats: mean/std/min/max for 7, 14, 28, 56 windows
  - Calendar features: dow, month, day, quarter, week_of_year, day_of_year
  - Fourier seasonality: sin/cos harmonics
  - Momentum and profile features: mom_7, mom_28, ratio_7_28, dow profile, doy profile

3. blend_alpha_0.90
- Weighted blend of optimized GBR and seasonal_year baseline:
  - Prediction = 0.90 * GBR + 0.10 * SeasonalYear

## Tuning Strategy
Grid searched compact candidate sets for practical runtime:
- Param set A: n_estimators=180, learning_rate=0.05, max_depth=3, subsample=0.9, min_samples_leaf=10
- Param set B: n_estimators=260, learning_rate=0.035, max_depth=4, subsample=0.85, min_samples_leaf=12
- Blend alpha candidates: 0.75, 0.90

Best tuning configuration selected by CV metrics:
- Params: set A
- Alpha: 0.90

## Validation Framework
- Expanding-window folds: 3
- Validation horizon per fold: 120 days
- Metrics: MAE, RMSE, R2

## Model Comparison (M7)
From outputs/tables/m7_model_comparison.csv

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| blend_alpha_0.90 | 677003.83 | 908371.80 | 0.5784 |
| gbr_recursive | 683882.70 | 913893.11 | 0.5771 |
| seasonal_year_lag365 | 837446.12 | 1134986.03 | 0.2843 |

Selected final inference model: blend_alpha_0.90

## Lift vs Milestone 6 Baseline
M6 best baseline was seasonal_year_lag365:
- MAE: 837446.12
- RMSE: 1134986.03
- R2: 0.2843

M7 selected model (blend_alpha_0.90):
- MAE: 677003.83
- RMSE: 908371.80
- R2: 0.5784

Measured lift:
- MAE improvement: about 19.2% lower
- RMSE improvement: about 20.0% lower
- R2 increase: +0.2941 absolute

## Generated Artifacts
Script:
- scripts/m7_forecasting_optimization.py

Tables:
- outputs/tables/m7_tuning_results.csv
- outputs/tables/m7_backtest_fold_metrics.csv
- outputs/tables/m7_model_comparison.csv
- outputs/tables/m7_backtest_daily_predictions.csv
- outputs/tables/m7_test_forecast_detail.csv

Submission:
- outputs/submissions/m7_submission_optimized.csv

## Selection Rationale
The blend beat both standalone models on all three competition metrics in CV average. It keeps the seasonal baseline signal while correcting local error patterns using boosted lag/rolling dynamics.

## Reproducibility
Run:

```powershell
python scripts\m7_forecasting_optimization.py
```

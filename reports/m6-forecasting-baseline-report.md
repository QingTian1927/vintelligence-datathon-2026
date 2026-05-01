# Milestone 6: Forecasting Baseline Report

Execution date: 2026-04-27

## Objective
Build a leakage-safe baseline forecasting pipeline for Part 3 (Sales Forecasting), evaluated with time-ordered validation and exported as a Kaggle-ready submission file.

## Competition Rule Alignment
- Train window used for modeling: 2012-07-04 to 2022-12-31 (`sales.csv`).
- Forecast horizon: 2023-01-01 to 2024-07-01 (same as `sample_submission.csv`).
- No external data used.
- No use of test `Revenue` or test `COGS` as model features.
- Time-aware backtesting (no random split).
- Submission row order preserved exactly as `sample_submission.csv`.
- Random seed fixed: 42.

## Baseline Methods Implemented
1. `seasonal_week_lag7`
- Recursive seasonal naive using last 7-day lag.

2. `seasonal_year_lag365`
- Recursive seasonal naive using last 365-day lag.

3. `linear_recursive_lagged`
- Linear regression with only train-history features:
  - Calendar: day-of-week, month, day, day-of-year, sin/cos day-of-year, trend index
  - Lags: 1, 7, 14, 28, 56, 365
  - Rolling means: 7-day, 28-day
- Recursive rollout for multi-step forecasting.

4. `ensemble_equal_weight`
- Equal-weight average of the three methods above.

## Validation Design
- Expanding-window, time-ordered backtesting.
- Folds: 3
- Validation horizon per fold: 120 days

Fold windows:
1. Train end: 2022-01-05, valid: 2022-01-06 to 2022-05-05
2. Train end: 2022-05-05, valid: 2022-05-06 to 2022-09-02
3. Train end: 2022-09-02, valid: 2022-09-03 to 2022-12-31

Metrics tracked:
- MAE (lower is better)
- RMSE (lower is better)
- R2 (higher is better)

## Backtest Summary (Average Across Folds)
| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| seasonal_year_lag365 | 837446.12 | 1134986.03 | 0.2843 |
| linear_recursive_lagged | 1091760.22 | 1372702.40 | -0.0099 |
| ensemble_equal_weight | 1182834.87 | 1487269.43 | -0.3395 |
| seasonal_week_lag7 | 2778316.38 | 3290596.11 | -8.9515 |

Selected baseline model for inference: `seasonal_year_lag365`

Reason for selection:
- Best MAE
- Best RMSE
- Best R2
- Best composite rank across all three metrics

## Generated Artifacts
Script:
- `scripts/m6_forecasting_baseline.py`

Tables:
- `outputs/tables/m6_backtest_fold_metrics.csv`
- `outputs/tables/m6_backtest_model_summary.csv`
- `outputs/tables/m6_backtest_daily_predictions.csv`
- `outputs/tables/m6_test_forecast_detail.csv`

Submission:
- `outputs/submissions/m6_submission_baseline.csv`

## Notes for Milestone 7 Optimization
Current baseline is robust and compliant but likely not leaderboard-optimal. Next improvements should focus on:
- Better seasonal/event modeling around Tet and peak promotions
- Hybrid models (LightGBM + statistical models)
- Better recursive stability for long horizons
- Time-series feature expansion from allowed internal data sources (`inventory.csv`, `web_traffic.csv`, promotions calendar)
- Fold-wise weight optimization for model ensembling

## Reproducibility
Run command:

```powershell
python scripts\m6_forecasting_baseline.py
```

Outputs are deterministic under the same environment and input files.

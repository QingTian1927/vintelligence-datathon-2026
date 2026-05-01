# Milestone 8: Explainability and Technical Report Content

Execution date: 2026-05-01

## Objective
Explain the optimized Part 3 forecasting model from Milestone 7 in business language, with leakage-safe evidence and transparent validation controls.

## Rule Compliance
- Only provided competition files were used.
- No external data.
- No hidden test Revenue or hidden test COGS were used as features.
- Explanation is built from train-history and a held-out historical slice only.
- Validation is time-ordered and reproducible.
- Random seed fixed at 42.

## Model Context
The explained model is the optimized Milestone 7 candidate:
- `blend_alpha_0.90` as the best CV performer
- Core learner: GradientBoostingRegressor trained on causal lag/rolling/calendar features
- Seasonal baseline retained as a reference signal

## Explainability Methods Used
1. Built-in tree feature importance
- Measures how often and how strongly a feature reduces error in the boosted trees.

2. Permutation importance
- Shuffles each feature on a held-out historical slice and measures degradation in RMSE.
- This confirms whether importance survives out-of-sample perturbation.

3. Grouped driver analysis
- Aggregates features into business-readable groups:
  - lag
  - rolling
  - calendar
  - seasonality
  - momentum

4. Partial-dependence-style sensitivity
- Replaces one feature across a grid of plausible values and observes the average prediction response.
- Used for the top drivers to show directional effects.

## Holdout Explainability Metrics
A historical 120-day holdout was used only for explanation and sanity validation.

- MAE: 401272.12
- RMSE: 529105.78
- R2: 0.6220

These are not the competition metrics, but they verify that the model behaves sensibly on unseen historical data.

## Key Driver Findings
From `outputs/tables/m8_feature_importance.csv` and `outputs/tables/m8_grouped_importance.csv`:

### 1. Short-term momentum is the strongest predictor
- `lag_1` is the dominant feature.
- Business meaning: tomorrow’s revenue is anchored heavily to yesterday’s realized demand.
- Interpretation: the series has strong persistence and limited day-to-day discontinuity.

### 2. Annual seasonality remains highly important
- `doy_profile` and `lag_365` are the next strongest drivers.
- Business meaning: the same calendar day in the previous year and the average revenue shape by day-of-year both matter materially.
- Interpretation: holidays, seasonal peaks, and annual cycles are structurally embedded in demand.

### 3. Recent local range matters more than long calendar features
- `roll_min_14`, `lag_7`, and `roll_min_7` appear among the top features.
- Business meaning: recent floor levels and weekly context help the model distinguish temporary spikes from true trend shifts.
- Interpretation: the model is using short-range stability as a guardrail.

### 4. Trend contributes but does not dominate
- `trend_idx` ranks below the top lag/seasonal features.
- Business meaning: there is long-run growth, but the strongest predictive signal is still immediate history plus seasonal recurrence.
- Interpretation: the model is not simply memorizing a straight upward line.

### 5. Momentum features help, but mostly as refinements
- `mom_7`, `mom_28`, and `ratio_7_28` contribute modestly.
- Business meaning: the model uses acceleration/deceleration signals, but they are secondary to lag structure.

## Grouped Interpretation
Grouped importance shares:
- Lag features: 74.27%
- Seasonality features: 14.02%
- Rolling features: 6.17%
- Calendar features: 3.28%
- Momentum features: 0.85%

### Business reading
The model is primarily a demand persistence model with strong seasonal anchoring.
That is consistent with an e-commerce fashion business where:
- yesterday’s demand informs near-term demand,
- annual events and holiday timing matter materially,
- and short rolling windows capture operational surges or cooling periods.

## Partial Dependence Sensitivity
The top three drivers were examined:
- `lag_1`
- `doy_profile`
- `lag_365`

### Directional conclusions
- Higher `lag_1` values map to higher forecasted revenue.
- Higher `doy_profile` values also lift forecasted revenue.
- `lag_365` provides a stable year-ago anchor; higher prior-year same-day values raise the forecast, but with less sensitivity than `lag_1`.

### Business interpretation
- Revenue forecasting is most sensitive to very recent demand.
- Long-cycle seasonal expectations are the second-order stabilizer.
- This is an intuitive structure for planning inventory and promotion timing.

## Why This Model Is Trustworthy
- The explainability tables are derived from a held-out historical slice, not from the hidden competition test.
- The feature rankings are consistent across built-in importance, permutation importance, and grouped analysis.
- The top features are interpretable and align with business logic.
- The model avoids non-causal shortcuts like using future revenue or hidden labels.

## Generated Evidence Files
- `outputs/tables/m8_feature_importance.csv`
- `outputs/tables/m8_permutation_importance.csv`
- `outputs/tables/m8_grouped_importance.csv`
- `outputs/tables/m8_partial_dependence_sensitivity.csv`
- `outputs/tables/m8_explainability_summary.csv`

## Suggested Report Insert for Part 3
Use the following high-level explanation in the competition report:

> The optimized forecasting model is dominated by recent demand persistence and annual seasonality. The strongest driver is yesterday’s revenue, followed by day-of-year seasonal profiles and the same day last year. This indicates that the model learns a stable retail demand process with strong short-term autocorrelation and recurring calendar effects. Such behavior is business-plausible for a fashion e-commerce company where promotions, holidays, and recent sales momentum strongly shape near-term demand.

## Reproducibility
Run:

```powershell
python scripts\m8_explainability.py
```

This regenerates all explanation tables under `outputs/tables/`.

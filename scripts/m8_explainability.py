"""
Milestone 8: Explainability and Technical Report Content (Part 3)

Goal:
- Explain the optimized forecasting model from Milestone 7.
- Use leakage-safe, train-only evidence.
- Provide feature importance, permutation importance, grouped driver analysis,
  and partial-dependence-style sensitivity for business interpretation.

Compliance:
- No external data.
- No hidden test Revenue/COGS as features.
- Uses only provided train history and time-aware validation.
- Reproducible with fixed seed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.m7_forecasting_optimization import (
    DATA_DIR,
    RANDOM_SEED,
    MAX_LAG,
    VALIDATION_HORIZON,
    build_folds,
    build_training_matrix,
    build_profiles_from_history,
    evaluate_predictions,
    forecast_gbr_recursive,
    forecast_seasonal_year,
    load_inputs,
    make_feature_row,
    summarize_model_metrics,
    train_gbr,
    tune_gbr_and_blend,
    validate_competition_windows,
)


OUTPUT_TABLE_DIR = Path("outputs/tables")
REPORT_DIR = Path("reports")

np.random.seed(RANDOM_SEED)


GROUP_MAP = {
    "lag": ["lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_21", "lag_28", "lag_56", "lag_84", "lag_168", "lag_365"],
    "rolling": [
        "roll_mean_7", "roll_std_7", "roll_min_7", "roll_max_7",
        "roll_mean_14", "roll_std_14", "roll_min_14", "roll_max_14",
        "roll_mean_28", "roll_std_28", "roll_min_28", "roll_max_28",
        "roll_mean_56", "roll_std_56", "roll_min_56", "roll_max_56",
    ],
    "calendar": ["dow", "month", "day", "quarter", "week_of_year", "day_of_year", "is_weekend", "is_month_start", "is_month_end", "trend_idx"],
    "seasonality": ["sin_doy_1", "cos_doy_1", "sin_doy_2", "cos_doy_2", "dow_profile", "doy_profile"],
    "momentum": ["mom_7", "mom_28", "ratio_7_28"],
}


def ensure_dirs() -> None:
    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def build_feature_frame_for_analysis(train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X, y = build_training_matrix(train_df)
    return X.reset_index(drop=True), y.reset_index(drop=True)


def build_causal_feature_matrix(series_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    series_df = series_df.sort_values("Date").reset_index(drop=True)
    if len(series_df) <= MAX_LAG:
        raise ValueError("Need more history to build causal feature rows.")

    dates = series_df["Date"].tolist()
    values = series_df["Revenue"].tolist()

    rows = []
    targets = []

    for idx in range(MAX_LAG, len(series_df)):
        history_vals = values[:idx]
        history_dates = dates[:idx]
        profiles = build_profiles_from_history(history_dates, history_vals)
        rows.append(
            make_feature_row(
                date=dates[idx],
                history=history_vals,
                step_idx=idx,
                profiles=profiles,
            )
        )
        targets.append(values[idx])

    return pd.DataFrame(rows), pd.Series(targets, name="Revenue")


def build_validation_slice(sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid_days = VALIDATION_HORIZON
    train_df = sales.iloc[:-valid_days].copy().reset_index(drop=True)
    valid_df = sales.iloc[-valid_days:].copy().reset_index(drop=True)
    return train_df, valid_df


def top_feature_frame(model, X: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    feature_importance = pd.DataFrame(
        {
            "feature": X.columns,
            "feature_importance": model.feature_importances_,
        }
    ).sort_values("feature_importance", ascending=False)
    feature_importance["importance_share"] = feature_importance["feature_importance"] / feature_importance["feature_importance"].sum()
    feature_importance["rank"] = np.arange(1, len(feature_importance) + 1)
    return feature_importance.head(top_n).reset_index(drop=True)


def grouped_importance_table(feature_importance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group_name, features in GROUP_MAP.items():
        subset = feature_importance[feature_importance["feature"].isin(features)]
        rows.append(
            {
                "group": group_name,
                "feature_count": len(subset),
                "importance_share": float(subset["importance_share"].sum()),
                "top_feature": subset.iloc[0]["feature"] if not subset.empty else None,
            }
        )
    group_df = pd.DataFrame(rows).sort_values("importance_share", ascending=False).reset_index(drop=True)
    return group_df


def permutation_importance_table(model, X_valid: pd.DataFrame, y_valid: pd.Series) -> pd.DataFrame:
    result = permutation_importance(
        model,
        X_valid,
        y_valid,
        n_repeats=8,
        random_state=RANDOM_SEED,
        scoring="neg_root_mean_squared_error",
    )
    perm = pd.DataFrame(
        {
            "feature": X_valid.columns,
            "perm_importance_mean": result.importances_mean,
            "perm_importance_std": result.importances_std,
        }
    ).sort_values("perm_importance_mean", ascending=False)
    perm["rank"] = np.arange(1, len(perm) + 1)
    return perm.reset_index(drop=True)


def pdp_table(model, X: pd.DataFrame, feature_name: str, grid_size: int = 9) -> pd.DataFrame:
    quantiles = np.linspace(0.05, 0.95, grid_size)
    values = np.quantile(X[feature_name], quantiles)
    base = X.copy()
    preds = []
    for value in values:
        modified = base.copy()
        modified[feature_name] = value
        preds.append(float(np.mean(model.predict(modified))))
    return pd.DataFrame(
        {
            "feature": feature_name,
            "grid_value": values,
            "avg_prediction": preds,
        }
    )


def main() -> None:
    ensure_dirs()

    print("\n=== M8 EXPLAINABILITY PIPELINE ===")
    print(f"Random seed: {RANDOM_SEED}")

    sales, sample_submission = load_inputs()
    validate_competition_windows(sales, sample_submission)

    folds = build_folds(sales["Date"])
    best_params, best_alpha, tuning_df = tune_gbr_and_blend(sales, folds)
    fold_df, _ = None, None
    summary = None

    # Use the best tuned GBR for explainability, and the selected blend for context.
    train_df, valid_df = build_validation_slice(sales)
    X_train, y_train = build_feature_frame_for_analysis(train_df)
    combined_df = pd.concat([train_df, valid_df], ignore_index=True)
    X_all, y_all = build_causal_feature_matrix(combined_df)
    X_valid = X_all.iloc[-len(valid_df):].reset_index(drop=True)
    y_valid = y_all.iloc[-len(valid_df):].reset_index(drop=True)

    model, feature_cols = train_gbr(train_df, best_params)
    X_valid = X_valid[feature_cols]

    # Sanity metrics on the explainability holdout.
    pred_valid = model.predict(X_valid)
    explainer_metrics = evaluate_predictions(y_valid.to_numpy(dtype=float), pred_valid)

    feature_importance = top_feature_frame(model, X_train[feature_cols], top_n=20)
    group_importance = grouped_importance_table(feature_importance)
    perm_importance = permutation_importance_table(model, X_valid, y_valid)

    # Partial-dependence-style sensitivity for the top three drivers.
    pdp_frames = []
    for feature_name in feature_importance["feature"].head(3).tolist():
        pdp_frames.append(pdp_table(model, X_train[feature_cols], feature_name=feature_name, grid_size=9))
    pdp_df = pd.concat(pdp_frames, ignore_index=True)

    # Save evidence tables.
    feature_importance.to_csv(OUTPUT_TABLE_DIR / "m8_feature_importance.csv", index=False)
    perm_importance.to_csv(OUTPUT_TABLE_DIR / "m8_permutation_importance.csv", index=False)
    group_importance.to_csv(OUTPUT_TABLE_DIR / "m8_grouped_importance.csv", index=False)
    pdp_df.to_csv(OUTPUT_TABLE_DIR / "m8_partial_dependence_sensitivity.csv", index=False)

    explanation_summary = pd.DataFrame(
        [
            {
                "metric": "MAE",
                "value": explainer_metrics["MAE"],
            },
            {
                "metric": "RMSE",
                "value": explainer_metrics["RMSE"],
            },
            {
                "metric": "R2",
                "value": explainer_metrics["R2"],
            },
            {
                "metric": "best_blend_alpha",
                "value": best_alpha,
            },
        ]
    )
    explanation_summary.to_csv(OUTPUT_TABLE_DIR / "m8_explainability_summary.csv", index=False)

    print("\nExplainability holdout metrics:")
    print(explainer_metrics)
    print("\nTop features:")
    print(feature_importance.head(10).to_string(index=False))
    print("\nGrouped importance:")
    print(group_importance.to_string(index=False))

    print("\nSaved outputs:")
    print("  - outputs/tables/m8_feature_importance.csv")
    print("  - outputs/tables/m8_permutation_importance.csv")
    print("  - outputs/tables/m8_grouped_importance.csv")
    print("  - outputs/tables/m8_partial_dependence_sensitivity.csv")
    print("  - outputs/tables/m8_explainability_summary.csv")


if __name__ == "__main__":
    main()

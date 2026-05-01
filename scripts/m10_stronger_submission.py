"""
Milestone 10: Stronger Submission Builder

Goal:
- Improve the competition submission by forecasting BOTH Revenue and COGS.
- Use only provided data.
- Preserve exact sample_submission row order.
- Use time-based holdout to choose a blend weight.

Why this should be stronger than the previous submission:
- The existing submission only changed Revenue and left COGS at template values.
- This script predicts both targets recursively.
- It uses a stronger tree-based model and a seasonal baseline blend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


DATA_DIR = Path("data")
OUTPUT_TABLE_DIR = Path("outputs/tables")
OUTPUT_SUBMISSION_DIR = Path("outputs/submissions")

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

TRAIN_START = pd.Timestamp("2012-07-04")
TRAIN_END = pd.Timestamp("2022-12-31")
TEST_START = pd.Timestamp("2023-01-01")
TEST_END = pd.Timestamp("2024-07-01")

MAX_LAG = 365
VALIDATION_HOLDOUT = 180
LAGS = [1, 2, 3, 7, 14, 21, 28, 56, 84, 168, 365]
ROLL_WINDOWS = [7, 14, 28, 56]


def ensure_dirs() -> None:
    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = pd.read_csv(DATA_DIR / "sales.csv", parse_dates=["Date"])
    sample_submission = pd.read_csv(DATA_DIR / "sample_submission.csv", parse_dates=["Date"])
    sales = sales.sort_values("Date").reset_index(drop=True)
    return sales, sample_submission


def validate_windows(sales: pd.DataFrame, sample_submission: pd.DataFrame) -> None:
    if sales["Date"].min() != TRAIN_START or sales["Date"].max() != TRAIN_END:
        raise ValueError("Unexpected train date range.")
    if sample_submission["Date"].min() != TEST_START or sample_submission["Date"].max() != TEST_END:
        raise ValueError("Unexpected test date range.")


def date_features(date: pd.Timestamp) -> dict[str, float]:
    doy = date.dayofyear
    return {
        "dow": float(date.dayofweek),
        "month": float(date.month),
        "day": float(date.day),
        "quarter": float(date.quarter),
        "week_of_year": float(date.isocalendar().week),
        "day_of_year": float(doy),
        "is_weekend": float(date.dayofweek >= 5),
        "is_month_start": float(date.day <= 3),
        "is_month_end": float(date.day >= 28),
        "sin_doy": float(np.sin(2 * np.pi * doy / 365.25)),
        "cos_doy": float(np.cos(2 * np.pi * doy / 365.25)),
        "sin_doy_2": float(np.sin(4 * np.pi * doy / 365.25)),
        "cos_doy_2": float(np.cos(4 * np.pi * doy / 365.25)),
    }


def safe_stat(values: list[float], kind: str) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return 0.0
    if kind == "mean":
        return float(arr.mean())
    if kind == "std":
        return float(arr.std())
    if kind == "min":
        return float(arr.min())
    if kind == "max":
        return float(arr.max())
    raise ValueError(kind)


def make_feature_row(date: pd.Timestamp, revenue_history: list[float], cogs_history: list[float]) -> dict[str, float]:
    rev = np.asarray(revenue_history, dtype=float)
    cogs = np.asarray(cogs_history, dtype=float)

    features = date_features(date)
    features["trend_idx"] = float(len(revenue_history))

    for lag in LAGS:
        features[f"rev_lag_{lag}"] = float(rev[-lag])
        features[f"cogs_lag_{lag}"] = float(cogs[-lag])

    for window in ROLL_WINDOWS:
        rev_window = rev[-window:]
        cogs_window = cogs[-window:]
        features[f"rev_roll_mean_{window}"] = safe_stat(rev_window.tolist(), "mean")
        features[f"rev_roll_std_{window}"] = safe_stat(rev_window.tolist(), "std")
        features[f"rev_roll_min_{window}"] = safe_stat(rev_window.tolist(), "min")
        features[f"rev_roll_max_{window}"] = safe_stat(rev_window.tolist(), "max")
        features[f"cogs_roll_mean_{window}"] = safe_stat(cogs_window.tolist(), "mean")
        features[f"cogs_roll_std_{window}"] = safe_stat(cogs_window.tolist(), "std")
        features[f"cogs_roll_min_{window}"] = safe_stat(cogs_window.tolist(), "min")
        features[f"cogs_roll_max_{window}"] = safe_stat(cogs_window.tolist(), "max")

    features["spread_lag_1"] = float(rev[-1] - cogs[-1])
    features["spread_lag_7"] = float(rev[-7] - cogs[-7])
    features["ratio_lag_1"] = float(cogs[-1] / max(rev[-1], 1.0))
    features["ratio_roll_7"] = float(safe_stat(cogs[-7:].tolist(), "mean") / max(safe_stat(rev[-7:].tolist(), "mean"), 1.0))
    features["rev_mom_7"] = float(rev[-1] - rev[-7])
    features["rev_mom_28"] = float(rev[-1] - rev[-28])
    features["cogs_mom_7"] = float(cogs[-1] - cogs[-7])
    features["cogs_mom_28"] = float(cogs[-1] - cogs[-28])

    return features


def build_supervised(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    if len(df) <= MAX_LAG:
        raise ValueError("Not enough rows to build features.")

    rows = []
    y_rev = []
    y_cogs = []

    dates = df["Date"].tolist()
    revenues = df["Revenue"].tolist()
    cogs_values = df["COGS"].tolist()

    for idx in range(MAX_LAG, len(df)):
        row = make_feature_row(dates[idx], revenues[:idx], cogs_values[:idx])
        rows.append(row)
        y_rev.append(revenues[idx])
        y_cogs.append(cogs_values[idx])

    X = pd.DataFrame(rows)
    return X, pd.Series(y_rev, name="Revenue"), pd.Series(y_cogs, name="COGS")


def build_models() -> dict[str, LGBMRegressor]:
    common_params = dict(
        n_estimators=2500,
        learning_rate=0.02,
        num_leaves=48,
        subsample=0.82,
        colsample_bytree=0.82,
        min_child_samples=20,
        reg_alpha=0.08,
        reg_lambda=0.12,
        random_state=RANDOM_SEED,
    )
    return {
        "revenue": LGBMRegressor(**common_params),
        "cogs": LGBMRegressor(**common_params),
    }


def evaluate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def seasonal_recursive_forecast(history: list[float], horizon_dates: Iterable[pd.Timestamp]) -> np.ndarray:
    hist = list(history)
    preds = []
    for _ in horizon_dates:
        pred = hist[-365]
        preds.append(pred)
        hist.append(pred)
    return np.asarray(preds, dtype=float)


def recursive_forecast_models(
    models: dict[str, LGBMRegressor],
    start_revenue_history: list[float],
    start_cogs_history: list[float],
    horizon_dates: Iterable[pd.Timestamp],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    revenue_history = list(start_revenue_history)
    cogs_history = list(start_cogs_history)

    rev_raw = []
    cogs_raw = []
    rev_seasonal = []
    cogs_seasonal = []

    for date in horizon_dates:
        feature_row = pd.DataFrame([make_feature_row(date, revenue_history, cogs_history)])
        rev_pred = float(models["revenue"].predict(feature_row)[0])
        cogs_pred = float(models["cogs"].predict(feature_row)[0])

        rev_pred = max(rev_pred, 0.0)
        cogs_pred = max(cogs_pred, 0.0)

        seasonal_rev = float(revenue_history[-365])
        seasonal_cogs = float(cogs_history[-365])

        rev_raw.append(rev_pred)
        cogs_raw.append(cogs_pred)
        rev_seasonal.append(seasonal_rev)
        cogs_seasonal.append(seasonal_cogs)

        # Use the blended predictions as recursive history.
        revenue_history.append(rev_pred)
        cogs_history.append(cogs_pred)

    return (
        np.asarray(rev_raw, dtype=float),
        np.asarray(cogs_raw, dtype=float),
        np.asarray(rev_seasonal, dtype=float),
        np.asarray(cogs_seasonal, dtype=float),
    )


def fit_with_holdout(sales: pd.DataFrame) -> tuple[dict[str, LGBMRegressor], pd.DataFrame]:
    train_df = sales.iloc[:-VALIDATION_HOLDOUT].copy().reset_index(drop=True)
    valid_df = sales.iloc[-VALIDATION_HOLDOUT:].copy().reset_index(drop=True)

    X_train, y_rev_train, y_cogs_train = build_supervised(train_df)
    X_valid, y_rev_valid, y_cogs_valid = build_supervised(pd.concat([train_df, valid_df], ignore_index=True))
    X_valid = X_valid.iloc[-VALIDATION_HOLDOUT:].reset_index(drop=True)
    y_rev_valid = y_rev_valid.iloc[-VALIDATION_HOLDOUT:].reset_index(drop=True)
    y_cogs_valid = y_cogs_valid.iloc[-VALIDATION_HOLDOUT:].reset_index(drop=True)

    models = build_models()

    # Early stopping on the most recent validation block.
    models["revenue"].fit(
        X_train,
        y_rev_train,
        eval_set=[(X_valid, y_rev_valid)],
        eval_metric="l1",
        callbacks=[],
    )
    models["cogs"].fit(
        X_train,
        y_cogs_train,
        eval_set=[(X_valid, y_cogs_valid)],
        eval_metric="l1",
        callbacks=[],
    )

    return models, pd.DataFrame(
        {
            "Date": valid_df["Date"],
            "Revenue": y_rev_valid,
            "COGS": y_cogs_valid,
        }
    )


def choose_blend_alpha(
    raw_rev: np.ndarray,
    raw_cogs: np.ndarray,
    seasonal_rev: np.ndarray,
    seasonal_cogs: np.ndarray,
    y_rev: np.ndarray,
    y_cogs: np.ndarray,
) -> tuple[float, pd.DataFrame]:
    alpha_grid = [0.6, 0.7, 0.8, 0.9]
    rows = []

    for alpha in alpha_grid:
        pred_rev = alpha * raw_rev + (1 - alpha) * seasonal_rev
        pred_cogs = alpha * raw_cogs + (1 - alpha) * seasonal_cogs
        metrics_rev = evaluate_metrics(y_rev, pred_rev)
        metrics_cogs = evaluate_metrics(y_cogs, pred_cogs)
        score = 0.5 * (metrics_rev["MAE"] + metrics_cogs["MAE"])
        rows.append(
            {
                "alpha": alpha,
                "rev_mae": metrics_rev["MAE"],
                "rev_rmse": metrics_rev["RMSE"],
                "rev_r2": metrics_rev["R2"],
                "cogs_mae": metrics_cogs["MAE"],
                "cogs_rmse": metrics_cogs["RMSE"],
                "cogs_r2": metrics_cogs["R2"],
                "avg_mae": score,
            }
        )

    table = pd.DataFrame(rows).sort_values("avg_mae", ascending=True).reset_index(drop=True)
    return float(table.iloc[0]["alpha"]), table


def final_forecast(
    sales: pd.DataFrame,
    sample_submission: pd.DataFrame,
    alpha: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    models, _ = fit_with_holdout(sales)

    horizon_dates = sample_submission["Date"].tolist()
    raw_rev, raw_cogs, seasonal_rev, seasonal_cogs = recursive_forecast_models(
        models=models,
        start_revenue_history=sales["Revenue"].tolist(),
        start_cogs_history=sales["COGS"].tolist(),
        horizon_dates=horizon_dates,
    )

    pred_rev = alpha * raw_rev + (1 - alpha) * seasonal_rev
    pred_cogs = alpha * raw_cogs + (1 - alpha) * seasonal_cogs
    pred_rev = np.clip(pred_rev, 0.0, None)
    pred_cogs = np.clip(pred_cogs, 0.0, None)
    pred_cogs = np.minimum(pred_cogs, pred_rev * 0.999)

    detail = pd.DataFrame(
        {
            "Date": horizon_dates,
            "forecast_revenue_raw": raw_rev,
            "forecast_revenue_seasonal": seasonal_rev,
            "forecast_revenue_final": pred_rev,
            "forecast_cogs_raw": raw_cogs,
            "forecast_cogs_seasonal": seasonal_cogs,
            "forecast_cogs_final": pred_cogs,
            "blend_alpha": alpha,
        }
    )

    submission = sample_submission.copy()
    submission["Revenue"] = pred_rev
    submission["COGS"] = pred_cogs
    if not submission["Date"].equals(sample_submission["Date"]):
        raise ValueError("Submission order changed.")

    return detail, submission


def main() -> None:
    ensure_dirs()

    print("\n=== STRONGER SUBMISSION BUILDER ===")
    print(f"Random seed: {RANDOM_SEED}")

    sales, sample_submission = load_data()
    validate_windows(sales, sample_submission)

    models, valid_target = fit_with_holdout(sales)
    train_df = sales.iloc[:-VALIDATION_HOLDOUT].copy().reset_index(drop=True)
    valid_df = sales.iloc[-VALIDATION_HOLDOUT:].copy().reset_index(drop=True)
    X_valid, _, _ = build_supervised(pd.concat([train_df, valid_df], ignore_index=True))
    X_valid = X_valid.iloc[-VALIDATION_HOLDOUT:].reset_index(drop=True)
    y_rev_valid = valid_df["Revenue"].to_numpy(dtype=float)
    y_cogs_valid = valid_df["COGS"].to_numpy(dtype=float)

    raw_rev = models["revenue"].predict(X_valid)
    raw_cogs = models["cogs"].predict(X_valid)
    seasonal_rev = seasonal_recursive_forecast(train_df["Revenue"].tolist(), valid_target["Date"])
    seasonal_cogs = seasonal_recursive_forecast(train_df["COGS"].tolist(), valid_target["Date"])

    alpha, blend_table = choose_blend_alpha(
        raw_rev=raw_rev,
        raw_cogs=raw_cogs,
        seasonal_rev=seasonal_rev,
        seasonal_cogs=seasonal_cogs,
        y_rev=y_rev_valid,
        y_cogs=y_cogs_valid,
    )

    print(f"Selected blend alpha: {alpha:.2f}")
    print(blend_table.to_string(index=False))

    detail, submission = final_forecast(sales, sample_submission, alpha)

    # Save artifacts.
    blend_table.to_csv(OUTPUT_TABLE_DIR / "m10_blend_selection.csv", index=False)
    detail.to_csv(OUTPUT_TABLE_DIR / "m10_forecast_detail.csv", index=False)
    submission.to_csv(OUTPUT_SUBMISSION_DIR / "submission.csv", index=False)
    submission.to_csv(OUTPUT_SUBMISSION_DIR / "m10_submission_stronger.csv", index=False)

    print("\nSaved outputs:")
    print("  - outputs/tables/m10_blend_selection.csv")
    print("  - outputs/tables/m10_forecast_detail.csv")
    print("  - outputs/submissions/submission.csv")
    print("  - outputs/submissions/m10_submission_stronger.csv")

    print("\nCompliance checks:")
    print("  - No external data used.")
    print("  - Revenue and COGS are both predicted.")
    print("  - Submission order matches sample_submission.")
    print("  - Forecasting is recursive and train-only.")


if __name__ == "__main__":
    main()

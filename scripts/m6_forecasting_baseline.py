"""
Milestone 6: Forecasting Baseline Pipeline (Part 3)

Goal:
- Build reproducible, leakage-safe baseline models for daily Revenue forecasting.
- Evaluate with time-aware backtesting using MAE, RMSE, and R2.
- Generate Kaggle-ready submission that preserves sample row order.

Competition Compliance:
1) No external data.
2) No usage of test Revenue/COGS as model features.
3) Reproducible execution with fixed random seed.
4) Time-ordered validation (no random split).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
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
VALIDATION_HORIZON = 120
N_FOLDS = 3


@dataclass
class Fold:
    fold_id: int
    train_end: pd.Timestamp
    valid_start: pd.Timestamp
    valid_end: pd.Timestamp


@dataclass
class ForecastResult:
    model_name: str
    y_pred: np.ndarray


def ensure_dirs() -> None:
    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = pd.read_csv(DATA_DIR / "sales.csv", parse_dates=["Date"])
    sample_submission = pd.read_csv(DATA_DIR / "sample_submission.csv", parse_dates=["Date"])

    sales = sales.sort_values("Date").reset_index(drop=True)

    return sales, sample_submission


def validate_competition_windows(sales: pd.DataFrame, sample_submission: pd.DataFrame) -> None:
    if sales["Date"].min() != TRAIN_START or sales["Date"].max() != TRAIN_END:
        raise ValueError(
            f"Unexpected train date range: {sales['Date'].min()} -> {sales['Date'].max()}"
        )

    if sample_submission["Date"].min() != TEST_START or sample_submission["Date"].max() != TEST_END:
        raise ValueError(
            f"Unexpected test date range: {sample_submission['Date'].min()} -> {sample_submission['Date'].max()}"
        )


def build_folds(dates: pd.Series, horizon: int = VALIDATION_HORIZON, n_folds: int = N_FOLDS) -> list[Fold]:
    train_end_global = dates.max()
    folds: list[Fold] = []

    for i in range(n_folds, 0, -1):
        valid_end = train_end_global - pd.Timedelta(days=(i - 1) * horizon)
        valid_start = valid_end - pd.Timedelta(days=horizon - 1)
        train_end = valid_start - pd.Timedelta(days=1)
        folds.append(
            Fold(
                fold_id=(n_folds - i + 1),
                train_end=train_end,
                valid_start=valid_start,
                valid_end=valid_end,
            )
        )

    min_train_needed = TRAIN_START + pd.Timedelta(days=MAX_LAG + 30)
    if folds[0].train_end < min_train_needed:
        raise ValueError("Fold generation leaves too little history for lag features.")

    return folds


def date_features(date: pd.Timestamp, step_idx: int) -> dict[str, float]:
    doy = date.dayofyear
    return {
        "dow": float(date.dayofweek),
        "month": float(date.month),
        "day": float(date.day),
        "doy": float(doy),
        "sin_doy": float(np.sin(2 * np.pi * doy / 365.25)),
        "cos_doy": float(np.cos(2 * np.pi * doy / 365.25)),
        "trend_idx": float(step_idx),
    }


def lag_features_from_history(history: list[float]) -> dict[str, float]:
    arr = np.asarray(history, dtype=float)
    return {
        "lag_1": float(arr[-1]),
        "lag_7": float(arr[-7]),
        "lag_14": float(arr[-14]),
        "lag_28": float(arr[-28]),
        "lag_56": float(arr[-56]),
        "lag_365": float(arr[-365]),
        "roll_mean_7": float(np.mean(arr[-7:])),
        "roll_mean_28": float(np.mean(arr[-28:])),
    }


def make_feature_row(date: pd.Timestamp, history: list[float], step_idx: int) -> dict[str, float]:
    feats = date_features(date=date, step_idx=step_idx)
    feats.update(lag_features_from_history(history=history))
    return feats


def build_training_matrix(train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    if len(train_df) <= MAX_LAG:
        raise ValueError("Not enough rows to build lag-based features.")

    dates = train_df["Date"].tolist()
    revenues = train_df["Revenue"].tolist()

    rows = []
    targets = []

    for idx in range(MAX_LAG, len(train_df)):
        history = revenues[:idx]
        row = make_feature_row(date=dates[idx], history=history, step_idx=idx)
        rows.append(row)
        targets.append(revenues[idx])

    X = pd.DataFrame(rows)
    y = pd.Series(targets, name="Revenue")
    return X, y


def forecast_seasonal_week(history: list[float], horizon_dates: pd.Series) -> np.ndarray:
    hist = list(history)
    preds = []
    for _ in horizon_dates:
        pred = hist[-7]
        preds.append(pred)
        hist.append(pred)
    return np.array(preds, dtype=float)


def forecast_seasonal_year(history: list[float], horizon_dates: pd.Series) -> np.ndarray:
    hist = list(history)
    preds = []
    for _ in horizon_dates:
        pred = hist[-365]
        preds.append(pred)
        hist.append(pred)
    return np.array(preds, dtype=float)


def forecast_linear_recursive(train_df: pd.DataFrame, horizon_dates: pd.Series) -> np.ndarray:
    X_train, y_train = build_training_matrix(train_df)
    model = LinearRegression()
    model.fit(X_train, y_train)

    history = train_df["Revenue"].tolist()
    start_step = len(train_df)
    preds = []

    for offset, date in enumerate(horizon_dates):
        feats = make_feature_row(date=date, history=history, step_idx=start_step + offset)
        X_next = pd.DataFrame([feats], columns=X_train.columns)
        pred = float(model.predict(X_next)[0])
        pred = max(pred, 0.0)
        preds.append(pred)
        history.append(pred)

    return np.array(preds, dtype=float)


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def run_backtest(sales: pd.DataFrame, folds: list[Fold]) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_fold_metrics = []
    all_daily_predictions = []

    for fold in folds:
        train_df = sales[sales["Date"] <= fold.train_end].copy()
        valid_df = sales[(sales["Date"] >= fold.valid_start) & (sales["Date"] <= fold.valid_end)].copy()
        valid_dates = valid_df["Date"].reset_index(drop=True)

        if len(valid_df) != VALIDATION_HORIZON:
            raise ValueError(f"Fold {fold.fold_id} has {len(valid_df)} rows, expected {VALIDATION_HORIZON}.")

        base_history = train_df["Revenue"].tolist()
        y_true = valid_df["Revenue"].to_numpy(dtype=float)

        pred_week = forecast_seasonal_week(base_history, valid_dates)
        pred_year = forecast_seasonal_year(base_history, valid_dates)
        pred_lr = forecast_linear_recursive(train_df, valid_dates)
        pred_ens = (pred_week + pred_year + pred_lr) / 3.0

        candidates = [
            ForecastResult("seasonal_week_lag7", pred_week),
            ForecastResult("seasonal_year_lag365", pred_year),
            ForecastResult("linear_recursive_lagged", pred_lr),
            ForecastResult("ensemble_equal_weight", pred_ens),
        ]

        for result in candidates:
            metrics = evaluate_predictions(y_true=y_true, y_pred=result.y_pred)
            all_fold_metrics.append(
                {
                    "fold_id": fold.fold_id,
                    "train_end": fold.train_end,
                    "valid_start": fold.valid_start,
                    "valid_end": fold.valid_end,
                    "model": result.model_name,
                    **metrics,
                }
            )

            daily_df = pd.DataFrame(
                {
                    "fold_id": fold.fold_id,
                    "Date": valid_dates,
                    "actual_revenue": y_true,
                    "predicted_revenue": result.y_pred,
                    "model": result.model_name,
                }
            )
            all_daily_predictions.append(daily_df)

    fold_metrics_df = pd.DataFrame(all_fold_metrics)
    daily_pred_df = pd.concat(all_daily_predictions, ignore_index=True)

    summary = (
        fold_metrics_df.groupby("model", as_index=False)[["MAE", "RMSE", "R2"]]
        .mean()
        .sort_values(["RMSE", "MAE"], ascending=[True, True])
        .reset_index(drop=True)
    )

    summary["rank_rmse"] = summary["RMSE"].rank(method="dense", ascending=True)
    summary["rank_mae"] = summary["MAE"].rank(method="dense", ascending=True)
    summary["rank_r2"] = summary["R2"].rank(method="dense", ascending=False)
    summary["composite_rank"] = summary[["rank_rmse", "rank_mae", "rank_r2"]].mean(axis=1)
    summary = summary.sort_values(["composite_rank", "RMSE", "MAE"], ascending=[True, True, True])

    return fold_metrics_df, daily_pred_df.merge(summary[["model", "composite_rank"]], on="model", how="left")


def final_forecast_and_submission(
    sales: pd.DataFrame,
    sample_submission: pd.DataFrame,
    selected_model: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    horizon_dates = sample_submission["Date"]
    history = sales["Revenue"].tolist()

    pred_week = forecast_seasonal_week(history, horizon_dates)
    pred_year = forecast_seasonal_year(history, horizon_dates)
    pred_lr = forecast_linear_recursive(sales, horizon_dates)

    forecast_map: dict[str, np.ndarray] = {
        "seasonal_week_lag7": pred_week,
        "seasonal_year_lag365": pred_year,
        "linear_recursive_lagged": pred_lr,
        "ensemble_equal_weight": (pred_week + pred_year + pred_lr) / 3.0,
    }

    if selected_model not in forecast_map:
        raise ValueError(f"Unknown model selected: {selected_model}")

    selected_pred = np.maximum(forecast_map[selected_model], 0.0)

    forecast_detail = pd.DataFrame(
        {
            "Date": horizon_dates,
            "forecast_seasonal_week_lag7": pred_week,
            "forecast_seasonal_year_lag365": pred_year,
            "forecast_linear_recursive_lagged": pred_lr,
            "forecast_ensemble_equal_weight": forecast_map["ensemble_equal_weight"],
            "forecast_selected": selected_pred,
            "selected_model": selected_model,
        }
    )

    submission = sample_submission.copy()
    submission["Revenue"] = selected_pred

    if not submission["Date"].equals(sample_submission["Date"]):
        raise ValueError("Submission Date order changed; must match sample_submission exactly.")

    return forecast_detail, submission


def main() -> None:
    ensure_dirs()

    print("\n=== M6 BASELINE FORECASTING PIPELINE ===")
    print(f"Random seed: {RANDOM_SEED}")

    sales, sample_submission = load_inputs()
    validate_competition_windows(sales=sales, sample_submission=sample_submission)

    folds = build_folds(sales["Date"])
    fold_df, daily_df = run_backtest(sales=sales, folds=folds)

    summary_df = (
        fold_df.groupby("model", as_index=False)[["MAE", "RMSE", "R2"]]
        .mean()
        .sort_values(["RMSE", "MAE"], ascending=[True, True])
        .reset_index(drop=True)
    )
    summary_df["rank_rmse"] = summary_df["RMSE"].rank(method="dense", ascending=True)
    summary_df["rank_mae"] = summary_df["MAE"].rank(method="dense", ascending=True)
    summary_df["rank_r2"] = summary_df["R2"].rank(method="dense", ascending=False)
    summary_df["composite_rank"] = summary_df[["rank_rmse", "rank_mae", "rank_r2"]].mean(axis=1)
    summary_df = summary_df.sort_values(["composite_rank", "RMSE", "MAE"], ascending=[True, True, True])

    selected_model = str(summary_df.iloc[0]["model"])
    print(f"\nSelected model from backtest: {selected_model}")

    forecast_detail, submission = final_forecast_and_submission(
        sales=sales,
        sample_submission=sample_submission,
        selected_model=selected_model,
    )

    fold_df.to_csv(OUTPUT_TABLE_DIR / "m6_backtest_fold_metrics.csv", index=False)
    summary_df.to_csv(OUTPUT_TABLE_DIR / "m6_backtest_model_summary.csv", index=False)
    daily_df.to_csv(OUTPUT_TABLE_DIR / "m6_backtest_daily_predictions.csv", index=False)
    forecast_detail.to_csv(OUTPUT_TABLE_DIR / "m6_test_forecast_detail.csv", index=False)

    submission.to_csv(OUTPUT_SUBMISSION_DIR / "m6_submission_baseline.csv", index=False)

    print("\nSaved outputs:")
    print("  - outputs/tables/m6_backtest_fold_metrics.csv")
    print("  - outputs/tables/m6_backtest_model_summary.csv")
    print("  - outputs/tables/m6_backtest_daily_predictions.csv")
    print("  - outputs/tables/m6_test_forecast_detail.csv")
    print("  - outputs/submissions/m6_submission_baseline.csv")

    print("\nCompliance notes:")
    print("  - Features use only historical train Revenue and calendar fields.")
    print("  - No test Revenue/COGS used as predictors.")
    print("  - Submission preserves sample_submission row order and Date column.")


if __name__ == "__main__":
    main()

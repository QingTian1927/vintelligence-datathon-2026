"""
Milestone 7: Forecasting Optimization and Ensembling (Part 3)

What this script does:
- Builds enhanced lag/rolling/calendar features from train history only.
- Tunes gradient boosting model with time-aware folds.
- Compares optimized model vs strong seasonal baseline.
- Selects best blend/model based on MAE, RMSE, R2.
- Generates competition-compliant submission preserving sample row order.

Competition compliance:
- Uses only provided dataset files.
- Uses only train-period history for fitting features.
- Does not use test Revenue/COGS as features.
- Uses time-ordered validation and fixed random seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
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

    min_train_needed = TRAIN_START + pd.Timedelta(days=MAX_LAG + 60)
    if folds[0].train_end < min_train_needed:
        raise ValueError("Fold generation leaves too little history for lag features.")

    return folds


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def build_profiles_from_history(dates: list[pd.Timestamp], values: list[float]) -> dict[str, dict[int, float]]:
    profile_df = pd.DataFrame({"Date": dates, "Revenue": values})
    profile_df["dow"] = profile_df["Date"].dt.dayofweek
    profile_df["doy"] = profile_df["Date"].dt.dayofyear

    dow_map = profile_df.groupby("dow")["Revenue"].median().to_dict()
    doy_map = profile_df.groupby("doy")["Revenue"].median().to_dict()

    return {"dow_map": dow_map, "doy_map": doy_map}


def safe_stat(arr: np.ndarray, reducer: str) -> float:
    if arr.size == 0:
        return 0.0
    if reducer == "mean":
        return float(np.mean(arr))
    if reducer == "std":
        return float(np.std(arr))
    if reducer == "min":
        return float(np.min(arr))
    if reducer == "max":
        return float(np.max(arr))
    raise ValueError(f"Unknown reducer: {reducer}")


def make_feature_row(
    date: pd.Timestamp,
    history: list[float],
    step_idx: int,
    profiles: dict[str, dict[int, float]],
) -> dict[str, float]:
    arr = np.asarray(history, dtype=float)

    dow = date.dayofweek
    doy = date.dayofyear

    lag_keys = [1, 2, 3, 7, 14, 21, 28, 56, 84, 168, 365]
    lags = {f"lag_{k}": float(arr[-k]) for k in lag_keys}

    roll_windows = [7, 14, 28, 56]
    rolling = {}
    for w in roll_windows:
        segment = arr[-w:]
        rolling[f"roll_mean_{w}"] = safe_stat(segment, "mean")
        rolling[f"roll_std_{w}"] = safe_stat(segment, "std")
        rolling[f"roll_min_{w}"] = safe_stat(segment, "min")
        rolling[f"roll_max_{w}"] = safe_stat(segment, "max")

    # Trend and momentum proxies
    mom_7 = float(arr[-1] - arr[-7])
    mom_28 = float(arr[-1] - arr[-28])
    ratio_7_28 = float((rolling["roll_mean_7"] + 1.0) / (rolling["roll_mean_28"] + 1.0))

    # Calendar and Fourier-like seasonal terms
    week_of_year = date.isocalendar().week
    sin_doy_1 = float(np.sin(2 * np.pi * doy / 365.25))
    cos_doy_1 = float(np.cos(2 * np.pi * doy / 365.25))
    sin_doy_2 = float(np.sin(4 * np.pi * doy / 365.25))
    cos_doy_2 = float(np.cos(4 * np.pi * doy / 365.25))

    dow_profile = float(profiles["dow_map"].get(dow, rolling["roll_mean_28"]))
    doy_profile = float(profiles["doy_map"].get(doy, rolling["roll_mean_28"]))

    features = {
        "dow": float(dow),
        "month": float(date.month),
        "day": float(date.day),
        "quarter": float(date.quarter),
        "week_of_year": float(week_of_year),
        "day_of_year": float(doy),
        "is_weekend": float(1 if dow >= 5 else 0),
        "is_month_start": float(1 if date.day <= 3 else 0),
        "is_month_end": float(1 if date.day >= 28 else 0),
        "trend_idx": float(step_idx),
        "sin_doy_1": sin_doy_1,
        "cos_doy_1": cos_doy_1,
        "sin_doy_2": sin_doy_2,
        "cos_doy_2": cos_doy_2,
        "mom_7": mom_7,
        "mom_28": mom_28,
        "ratio_7_28": ratio_7_28,
        "dow_profile": dow_profile,
        "doy_profile": doy_profile,
    }

    features.update(lags)
    features.update(rolling)
    return features


def build_training_matrix(train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    if len(train_df) <= MAX_LAG:
        raise ValueError("Not enough rows to build lag features.")

    df = train_df.copy().reset_index(drop=True)
    profiles = build_profiles_from_history(df["Date"].tolist(), df["Revenue"].tolist())

    df["dow"] = df["Date"].dt.dayofweek.astype(float)
    df["month"] = df["Date"].dt.month.astype(float)
    df["day"] = df["Date"].dt.day.astype(float)
    df["quarter"] = df["Date"].dt.quarter.astype(float)
    df["week_of_year"] = df["Date"].dt.isocalendar().week.astype(float)
    df["day_of_year"] = df["Date"].dt.dayofyear.astype(float)
    df["is_weekend"] = (df["Date"].dt.dayofweek >= 5).astype(float)
    df["is_month_start"] = (df["Date"].dt.day <= 3).astype(float)
    df["is_month_end"] = (df["Date"].dt.day >= 28).astype(float)
    df["trend_idx"] = np.arange(len(df), dtype=float)

    df["sin_doy_1"] = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
    df["cos_doy_1"] = np.cos(2 * np.pi * df["day_of_year"] / 365.25)
    df["sin_doy_2"] = np.sin(4 * np.pi * df["day_of_year"] / 365.25)
    df["cos_doy_2"] = np.cos(4 * np.pi * df["day_of_year"] / 365.25)

    lag_keys = [1, 2, 3, 7, 14, 21, 28, 56, 84, 168, 365]
    for k in lag_keys:
        df[f"lag_{k}"] = df["Revenue"].shift(k)

    base = df["Revenue"].shift(1)
    for w in [7, 14, 28, 56]:
        roll = base.rolling(window=w)
        df[f"roll_mean_{w}"] = roll.mean()
        df[f"roll_std_{w}"] = roll.std().fillna(0.0)
        df[f"roll_min_{w}"] = roll.min()
        df[f"roll_max_{w}"] = roll.max()

    df["mom_7"] = df["lag_1"] - df["lag_7"]
    df["mom_28"] = df["lag_1"] - df["lag_28"]
    df["ratio_7_28"] = (df["roll_mean_7"] + 1.0) / (df["roll_mean_28"] + 1.0)
    df["dow_profile"] = df["dow"].map(profiles["dow_map"]).astype(float)
    df["doy_profile"] = df["day_of_year"].map(profiles["doy_map"]).astype(float)

    feature_cols = [
        "dow", "month", "day", "quarter", "week_of_year", "day_of_year",
        "is_weekend", "is_month_start", "is_month_end", "trend_idx",
        "sin_doy_1", "cos_doy_1", "sin_doy_2", "cos_doy_2",
        "mom_7", "mom_28", "ratio_7_28", "dow_profile", "doy_profile",
        "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_21", "lag_28",
        "lag_56", "lag_84", "lag_168", "lag_365",
        "roll_mean_7", "roll_std_7", "roll_min_7", "roll_max_7",
        "roll_mean_14", "roll_std_14", "roll_min_14", "roll_max_14",
        "roll_mean_28", "roll_std_28", "roll_min_28", "roll_max_28",
        "roll_mean_56", "roll_std_56", "roll_min_56", "roll_max_56",
    ]

    usable = df.iloc[MAX_LAG:].dropna(subset=feature_cols).copy()
    X = usable[feature_cols].reset_index(drop=True)
    y = usable["Revenue"].reset_index(drop=True)
    return X, y


def forecast_seasonal_year(history: list[float], horizon_dates: pd.Series) -> np.ndarray:
    hist = list(history)
    preds = []
    for _ in horizon_dates:
        pred = hist[-365]
        preds.append(pred)
        hist.append(pred)
    return np.array(preds, dtype=float)


def train_gbr(train_df: pd.DataFrame, params: dict[str, Any]) -> tuple[GradientBoostingRegressor, list[str]]:
    X_train, y_train = build_training_matrix(train_df)
    model = GradientBoostingRegressor(
        random_state=RANDOM_SEED,
        loss="squared_error",
        **params,
    )
    model.fit(X_train, y_train)
    return model, list(X_train.columns)


def forecast_gbr_recursive(
    model: GradientBoostingRegressor,
    feature_columns: list[str],
    train_df: pd.DataFrame,
    horizon_dates: pd.Series,
) -> np.ndarray:
    history_vals = train_df["Revenue"].tolist()
    profiles = build_profiles_from_history(train_df["Date"].tolist(), history_vals)

    preds = []
    start_step = len(train_df)

    for offset, date in enumerate(horizon_dates):
        row = make_feature_row(
            date=date,
            history=history_vals,
            step_idx=start_step + offset,
            profiles=profiles,
        )
        X_next = pd.DataFrame([row], columns=feature_columns)
        pred = float(model.predict(X_next)[0])
        pred = max(pred, 0.0)

        preds.append(pred)
        history_vals.append(pred)

    return np.array(preds, dtype=float)


def evaluate_on_folds(
    sales: pd.DataFrame,
    folds: list[Fold],
    model_params: dict[str, Any],
    blend_alpha: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = []
    daily_records = []

    for fold in folds:
        train_df = sales[sales["Date"] <= fold.train_end].copy()
        valid_df = sales[(sales["Date"] >= fold.valid_start) & (sales["Date"] <= fold.valid_end)].copy()
        valid_dates = valid_df["Date"].reset_index(drop=True)
        y_true = valid_df["Revenue"].to_numpy(dtype=float)

        gbr_model, feature_cols = train_gbr(train_df, model_params)
        pred_gbr = forecast_gbr_recursive(gbr_model, feature_cols, train_df, valid_dates)
        pred_seasonal = forecast_seasonal_year(train_df["Revenue"].tolist(), valid_dates)
        pred_blend = blend_alpha * pred_gbr + (1.0 - blend_alpha) * pred_seasonal

        candidates = {
            "gbr_recursive": pred_gbr,
            "seasonal_year_lag365": pred_seasonal,
            f"blend_alpha_{blend_alpha:.2f}": pred_blend,
        }

        for model_name, y_pred in candidates.items():
            metrics = evaluate_predictions(y_true, y_pred)
            records.append(
                {
                    "fold_id": fold.fold_id,
                    "train_end": fold.train_end,
                    "valid_start": fold.valid_start,
                    "valid_end": fold.valid_end,
                    "model": model_name,
                    **metrics,
                }
            )

            daily_fold = pd.DataFrame(
                {
                    "fold_id": fold.fold_id,
                    "Date": valid_dates,
                    "actual_revenue": y_true,
                    "predicted_revenue": y_pred,
                    "model": model_name,
                }
            )
            daily_records.append(daily_fold)

    fold_df = pd.DataFrame(records)
    daily_df = pd.concat(daily_records, ignore_index=True)
    return fold_df, daily_df


def summarize_model_metrics(fold_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        fold_df.groupby("model", as_index=False)[["MAE", "RMSE", "R2"]]
        .mean()
        .sort_values(["RMSE", "MAE"], ascending=[True, True])
        .reset_index(drop=True)
    )

    summary["rank_rmse"] = summary["RMSE"].rank(method="dense", ascending=True)
    summary["rank_mae"] = summary["MAE"].rank(method="dense", ascending=True)
    summary["rank_r2"] = summary["R2"].rank(method="dense", ascending=False)
    summary["composite_rank"] = summary[["rank_rmse", "rank_mae", "rank_r2"]].mean(axis=1)
    summary = summary.sort_values(["composite_rank", "RMSE", "MAE"], ascending=[True, True, True])
    return summary


def tune_gbr_and_blend(sales: pd.DataFrame, folds: list[Fold]) -> tuple[dict[str, Any], float, pd.DataFrame]:
    param_grid: list[dict[str, Any]] = [
        {"n_estimators": 180, "learning_rate": 0.05, "max_depth": 3, "subsample": 0.9, "min_samples_leaf": 10},
        {"n_estimators": 260, "learning_rate": 0.035, "max_depth": 4, "subsample": 0.85, "min_samples_leaf": 12},
    ]
    alphas = [0.75, 0.9]

    tuning_rows = []

    for p_idx, params in enumerate(param_grid, start=1):
        for alpha in alphas:
            fold_df, _ = evaluate_on_folds(sales, folds, params, alpha)
            summary = summarize_model_metrics(fold_df)
            best_row = summary.iloc[0]
            tuning_rows.append(
                {
                    "param_set_id": p_idx,
                    "blend_alpha": alpha,
                    "best_model": best_row["model"],
                    "best_MAE": best_row["MAE"],
                    "best_RMSE": best_row["RMSE"],
                    "best_R2": best_row["R2"],
                    "composite_rank": best_row["composite_rank"],
                    "params": str(params),
                }
            )

    tuning_df = pd.DataFrame(tuning_rows).sort_values(
        ["best_RMSE", "best_MAE", "composite_rank"], ascending=[True, True, True]
    )

    best = tuning_df.iloc[0]
    best_params = param_grid[int(best["param_set_id"]) - 1]
    best_alpha = float(best["blend_alpha"])

    return best_params, best_alpha, tuning_df


def make_final_outputs(
    sales: pd.DataFrame,
    sample_submission: pd.DataFrame,
    best_params: dict[str, Any],
    best_alpha: float,
    selected_model: str,
) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    horizon_dates = sample_submission["Date"]

    gbr_model, feature_cols = train_gbr(sales, best_params)
    pred_gbr = forecast_gbr_recursive(gbr_model, feature_cols, sales, horizon_dates)
    pred_seasonal = forecast_seasonal_year(sales["Revenue"].tolist(), horizon_dates)
    pred_blend = best_alpha * pred_gbr + (1.0 - best_alpha) * pred_seasonal

    final_candidates = {
        "gbr_recursive": pred_gbr,
        "seasonal_year_lag365": pred_seasonal,
        f"blend_alpha_{best_alpha:.2f}": pred_blend,
    }
    if selected_model not in final_candidates:
        raise ValueError(f"Selected model '{selected_model}' not found in final candidates.")

    selected_pred = np.maximum(final_candidates[selected_model], 0.0)

    detail = pd.DataFrame(
        {
            "Date": horizon_dates,
            "forecast_gbr_recursive": pred_gbr,
            "forecast_seasonal_year_lag365": pred_seasonal,
            f"forecast_blend_alpha_{best_alpha:.2f}": pred_blend,
            "selected_model": selected_model,
            "forecast_selected": selected_pred,
        }
    )

    submission = sample_submission.copy()
    submission["Revenue"] = selected_pred
    if not submission["Date"].equals(sample_submission["Date"]):
        raise ValueError("Submission Date order changed; must match sample_submission exactly.")

    return selected_model, detail, submission


def main() -> None:
    ensure_dirs()

    print("\n=== M7 FORECASTING OPTIMIZATION PIPELINE ===")
    print(f"Random seed: {RANDOM_SEED}")

    sales, sample_submission = load_inputs()
    validate_competition_windows(sales, sample_submission)
    folds = build_folds(sales["Date"])

    best_params, best_alpha, tuning_df = tune_gbr_and_blend(sales, folds)
    print(f"\nBest tuning set: {best_params}")
    print(f"Best blend alpha: {best_alpha:.2f}")

    fold_df, daily_df = evaluate_on_folds(sales, folds, best_params, best_alpha)
    summary_df = summarize_model_metrics(fold_df)
    selected_model = str(summary_df.iloc[0]["model"])

    selected_model, forecast_detail, submission = make_final_outputs(
        sales=sales,
        sample_submission=sample_submission,
        best_params=best_params,
        best_alpha=best_alpha,
        selected_model=selected_model,
    )

    tuning_df.to_csv(OUTPUT_TABLE_DIR / "m7_tuning_results.csv", index=False)
    fold_df.to_csv(OUTPUT_TABLE_DIR / "m7_backtest_fold_metrics.csv", index=False)
    summary_df.to_csv(OUTPUT_TABLE_DIR / "m7_model_comparison.csv", index=False)
    daily_df.to_csv(OUTPUT_TABLE_DIR / "m7_backtest_daily_predictions.csv", index=False)
    forecast_detail.to_csv(OUTPUT_TABLE_DIR / "m7_test_forecast_detail.csv", index=False)
    submission.to_csv(OUTPUT_SUBMISSION_DIR / "m7_submission_optimized.csv", index=False)

    print("\nSelected final inference model:", selected_model)
    print("\nSaved outputs:")
    print("  - outputs/tables/m7_tuning_results.csv")
    print("  - outputs/tables/m7_backtest_fold_metrics.csv")
    print("  - outputs/tables/m7_model_comparison.csv")
    print("  - outputs/tables/m7_backtest_daily_predictions.csv")
    print("  - outputs/tables/m7_test_forecast_detail.csv")
    print("  - outputs/submissions/m7_submission_optimized.csv")

    print("\nCompliance notes:")
    print("  - Features built from train revenue history + calendar only.")
    print("  - No test Revenue/COGS features used.")
    print("  - Time-aware folds used for tuning and comparison.")
    print("  - Submission row order preserved from sample_submission.")


if __name__ == "__main__":
    main()

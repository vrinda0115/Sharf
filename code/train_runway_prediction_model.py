"""Train and evaluate SHARF's transparent 3-month runway prediction model.

The model is deliberately small and auditable: ridge regression predicts runway
months three months ahead from the operating metrics a founder can change in a
monthly review.  A chronological holdout avoids training on the future.  The
prediction interval combines historical residual uncertainty with feature-space
leverage, so unusual what-if inputs receive a wider interval.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "data" / "final"
HORIZON_MONTHS = 3
RIDGE_ALPHA = 1.0
FEATURES = [
    "monthly_revenue_usd",
    "cash_balance_usd",
    "monthly_burn_usd",
    "mom_revenue_growth",
    "monthly_churn_rate",
    "cac_payback_months",
    "nps",
    "headcount",
    "avg_time_to_fill_days",
    "governance_score",
]


def make_model_frame(metrics: pd.DataFrame) -> pd.DataFrame:
    """Align each feature month to the same startup's runway three months later."""
    frame = metrics.sort_values(["startup_id", "month"]).copy()
    frame["target_runway_months_3mo"] = frame.groupby("startup_id")["runway_months"].shift(-HORIZON_MONTHS)
    frame["target_month"] = frame.groupby("startup_id")["month"].shift(-HORIZON_MONTHS)
    return frame.dropna(subset=FEATURES + ["target_runway_months_3mo", "target_month"]).reset_index(drop=True)


def fit_ridge(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float, np.ndarray, np.ndarray, np.ndarray]:
    means = x.mean(axis=0)
    scales = x.std(axis=0, ddof=0)
    scales = np.where(scales == 0, 1.0, scales)
    z = (x - means) / scales
    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1]) * RIDGE_ALPHA
    penalty[0, 0] = 0.0
    inverse = np.linalg.pinv(design.T @ design + penalty)
    coefficients = inverse @ design.T @ y
    return coefficients, float(coefficients[0]), means, scales, inverse


def predict(x: np.ndarray, coefficients: np.ndarray, means: np.ndarray, scales: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    z = (x - means) / scales
    design = np.column_stack([np.ones(len(z)), z])
    return design @ coefficients, design


def main() -> None:
    metrics = pd.read_csv(FINAL_DIR / "sharf_monthly_metrics.csv", parse_dates=["month"])
    frame = make_model_frame(metrics)
    # All features are known at the prediction date.  Target months Oct-Dec are
    # held out for every startup, creating a true forward-in-time test set.
    cutoff = frame["target_month"].sort_values().unique()[-3]
    train = frame.loc[frame["target_month"] < cutoff].copy()
    test = frame.loc[frame["target_month"] >= cutoff].copy()
    x_train, y_train = train[FEATURES].to_numpy(float), train["target_runway_months_3mo"].to_numpy(float)
    x_test, y_test = test[FEATURES].to_numpy(float), test["target_runway_months_3mo"].to_numpy(float)
    coefficients, intercept, means, scales, inverse = fit_ridge(x_train, y_train)
    train_pred, _ = predict(x_train, coefficients, means, scales)
    test_pred, test_design = predict(x_test, coefficients, means, scales)
    residuals = y_train - train_pred
    residual_p05, residual_p95 = np.quantile(residuals, [0.05, 0.95])
    leverage = np.einsum("ij,jk,ik->i", test_design, inverse, test_design)
    scale = np.sqrt(1.0 + np.maximum(leverage, 0.0))
    lower = np.maximum(0.0, test_pred + residual_p05 * scale)
    upper = np.maximum(lower, test_pred + residual_p95 * scale)
    mae = float(np.mean(np.abs(y_test - test_pred)))
    rmse = float(np.sqrt(np.mean((y_test - test_pred) ** 2)))
    r2 = float(1 - np.sum((y_test - test_pred) ** 2) / np.sum((y_test - y_test.mean()) ** 2))
    coverage = float(np.mean((y_test >= lower) & (y_test <= upper)))

    predictions = test[["startup_id", "month", "target_month", "target_runway_months_3mo"]].copy()
    predictions["predicted_runway_months_3mo"] = test_pred.round(2)
    predictions["prediction_interval_lower_90"] = lower.round(2)
    predictions["prediction_interval_upper_90"] = upper.round(2)
    predictions["interval_contains_actual"] = ((y_test >= lower) & (y_test <= upper))
    predictions.to_csv(FINAL_DIR / "runway_model_holdout_predictions.csv", index=False)

    artifact = {
        "model_name": "Ridge regression with residual predictive interval",
        "target": "runway_months three months ahead",
        "horizon_months": HORIZON_MONTHS,
        "features": FEATURES,
        "feature_means": means.tolist(),
        "feature_scales": scales.tolist(),
        "feature_minimums": x_train.min(axis=0).tolist(),
        "feature_maximums": x_train.max(axis=0).tolist(),
        "coefficients": coefficients.tolist(),
        "ridge_alpha": RIDGE_ALPHA,
        "inverse_regularized_xtx": inverse.tolist(),
        "residual_p05": float(residual_p05),
        "residual_p95": float(residual_p95),
        "training_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_target_start": str(pd.Timestamp(cutoff).date()),
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2, "interval_coverage_90": coverage},
        "limitations": "Synthetic prototype data; interval reflects historical model residuals and feature distance, not a production guarantee.",
    }
    (FINAL_DIR / "runway_prediction_model.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Trained 3-month runway model: MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.3f}, coverage={coverage:.1%}")


if __name__ == "__main__":
    main()

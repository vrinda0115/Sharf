from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "data" / "final"


def check(name: str, passed: bool, details: str) -> dict[str, str | bool]:
    return {"check": name, "passed": bool(passed), "details": details}


def main() -> None:
    profiles = pd.read_csv(FINAL_DIR / "startup_profiles.csv")
    metrics = pd.read_csv(FINAL_DIR / "sharf_monthly_metrics.csv", parse_dates=["month"])
    forecast = pd.read_csv(FINAL_DIR / "monte_carlo_risk_forecast.csv", parse_dates=["forecast_start_month"])
    holdout = pd.read_csv(FINAL_DIR / "runway_model_holdout_predictions.csv")
    model = json.loads((FINAL_DIR / "runway_prediction_model.json").read_text(encoding="utf-8"))
    benchmark = pd.read_csv(FINAL_DIR / "company_employment_payroll_benchmark.csv")
    benchmark_summary = pd.read_csv(FINAL_DIR / "company_benchmark_summary.csv")
    results: list[dict[str, str | bool]] = []

    required_profile_cols = {
        "startup_id",
        "startup_name",
        "industry",
        "stage",
        "region",
        "founding_year",
        "board_or_advisory_group",
        "profile_source",
    }
    required_metric_cols = {
        "startup_id",
        "month",
        "monthly_revenue_usd",
        "cash_balance_usd",
        "monthly_burn_usd",
        "runway_months",
        "mom_revenue_growth",
        "monthly_churn_rate",
        "customer_acquisition_cost_usd",
        "cac_payback_months",
        "nps",
        "headcount",
        "avg_time_to_fill_days",
        "macro_stress_index",
        "sharf_score",
        "risk_tier",
        "burn_recommendation",
        "fundraising_readiness",
        "remediation_priority",
    }
    required_forecast_cols = {
        "startup_id",
        "forecast_start_month",
        "horizon_months",
        "simulation_count",
        "baseline_sharf_score",
        "expected_sharf_score_6mo",
        "p10_runway_months_6mo",
        "p50_runway_months_6mo",
        "p90_runway_months_6mo",
        "probability_cashout_6mo",
        "probability_critical_risk_6mo",
        "probability_runway_under_6mo",
        "monte_carlo_risk_label",
    }
    required_benchmark_cols = {
        "company_id",
        "company_name",
        "year",
        "employment",
        "payroll_usd",
        "payroll_per_employee_usd",
        "employment_growth",
        "payroll_growth",
    }
    results.append(check("profile_schema", required_profile_cols.issubset(profiles.columns), f"{len(profiles.columns)} columns present"))
    results.append(check("metric_schema", required_metric_cols.issubset(metrics.columns), f"{len(metrics.columns)} columns present"))
    results.append(check("monte_carlo_forecast_schema", required_forecast_cols.issubset(forecast.columns), f"{len(forecast.columns)} columns present"))
    results.append(check("company_benchmark_schema", required_benchmark_cols.issubset(benchmark.columns), f"{len(benchmark.columns)} columns present"))
    required_holdout_cols = {"startup_id", "target_runway_months_3mo", "predicted_runway_months_3mo", "prediction_interval_lower_90", "prediction_interval_upper_90", "interval_contains_actual"}
    results.append(check("predictive_model_holdout_schema", required_holdout_cols.issubset(holdout.columns), f"{len(holdout.columns)} columns present"))

    profile_ids_unique = profiles["startup_id"].is_unique
    metric_key_unique = not metrics.duplicated(["startup_id", "month"]).any()
    results.append(check("profile_identifier_uniqueness", profile_ids_unique, f"{profiles['startup_id'].nunique()} unique startup IDs"))
    results.append(check("metric_grain_uniqueness", metric_key_unique, "One row per startup-month"))

    missing_profile_keys = set(metrics["startup_id"]) - set(profiles["startup_id"])
    results.append(check("referential_integrity", len(missing_profile_keys) == 0, f"Missing profile keys: {sorted(missing_profile_keys)}"))
    missing_forecast_keys = set(forecast["startup_id"]) - set(profiles["startup_id"])
    results.append(check("forecast_referential_integrity", len(missing_forecast_keys) == 0, f"Missing forecast profile keys: {sorted(missing_forecast_keys)}"))

    missing_cells = int(metrics.isna().sum().sum() + profiles.isna().sum().sum() + forecast.isna().sum().sum())
    results.append(check("missingness", missing_cells == 0, f"{missing_cells} missing cells across final tables"))

    ranges = {
        "monthly_revenue_usd": (0, None),
        "cash_balance_usd": (0, None),
        "monthly_burn_usd": (1, None),
        "monthly_churn_rate": (0, 1),
        "gross_margin": (0, 1),
        "cac_payback_months": (0, 60),
        "nps": (-100, 100),
        "headcount": (1, None),
        "avg_time_to_fill_days": (1, 180),
        "macro_stress_index": (0, 1),
        "runway_months": (0, None),
        "sharf_score": (0, 100),
    }
    bad_ranges = []
    for col, (low, high) in ranges.items():
        ok = metrics[col].ge(low).all()
        if high is not None:
            ok = ok and metrics[col].le(high).all()
        if not ok:
            bad_ranges.append(col)
    results.append(check("range_checks", not bad_ranges, f"Out-of-range columns: {bad_ranges or 'none'}"))

    forecast_probability_cols = [
        "probability_cashout_6mo",
        "probability_critical_risk_6mo",
        "probability_runway_under_6mo",
    ]
    probability_ok = forecast[forecast_probability_cols].ge(0).all().all() and forecast[forecast_probability_cols].le(1).all().all()
    forecast_score_ok = forecast["expected_sharf_score_6mo"].between(0, 100).all()
    forecast_quantile_ok = (
        (forecast["p10_runway_months_6mo"] <= forecast["p50_runway_months_6mo"])
        & (forecast["p50_runway_months_6mo"] <= forecast["p90_runway_months_6mo"])
    ).all()
    simulation_count_ok = forecast["simulation_count"].eq(1000).all()
    results.append(
        check(
            "monte_carlo_output_checks",
            probability_ok and forecast_score_ok and forecast_quantile_ok and simulation_count_ok,
            "Probabilities, scores, quantiles, and simulation counts are valid",
        )
    )

    interval_ok = (holdout["prediction_interval_lower_90"] <= holdout["prediction_interval_upper_90"]).all() and holdout["prediction_interval_lower_90"].ge(0).all()
    metric_ok = all(np.isfinite(float(model["metrics"][name])) for name in ["mae", "rmse", "r2", "interval_coverage_90"])
    split_ok = int(model["training_rows"]) > 0 and int(model["test_rows"]) == len(holdout) and int(model["horizon_months"]) == 3
    results.append(check("predictive_model_outputs", interval_ok and metric_ok and split_ok, "Temporal holdout, finite performance metrics, and ordered 90% prediction intervals are valid"))

    runway_delta = (metrics["runway_months"] - metrics["cash_balance_usd"] / metrics["monthly_burn_usd"]).abs().max()
    results.append(check("runway_formula", runway_delta <= 0.02, f"Maximum formula difference: {runway_delta:.4f}"))

    valid_risk_tiers = set(metrics["risk_tier"]).issubset({"Critical", "Watch", "Stable"})
    valid_recommendations = (
        metrics["burn_recommendation"].notna().all()
        and metrics["fundraising_readiness"].notna().all()
        and metrics["remediation_priority"].notna().all()
    )
    results.append(check("decision_outputs_present", valid_risk_tiers and valid_recommendations, "All rows have risk and recommendation outputs"))

    score_inputs = [
        "runway_score",
        "revenue_score",
        "retention_score",
        "growth_efficiency_score",
        "customer_sentiment_score",
        "team_capacity_score",
        "governance_score",
    ]
    metrics_computable = metrics[score_inputs + ["sharf_score"]].apply(pd.to_numeric, errors="coerce").notna().all().all()
    results.append(check("planned_metrics_computable", metrics_computable, "All scoring inputs and final SHARF score are numeric"))

    by_month_counts = metrics.groupby("startup_id")["month"].nunique()
    results.append(check("time_coverage", by_month_counts.eq(12).all(), f"{len(by_month_counts)} startups have 12 monthly observations"))
    results.append(check("forecast_coverage", len(forecast) == len(profiles), f"{len(forecast)} forecast rows for {len(profiles)} profiles"))
    benchmark_year_ok = benchmark["year"].between(2010, 2025).all()
    benchmark_summary_ok = (
        len(benchmark_summary) == 1
        and int(benchmark_summary.loc[0, "row_count"]) == len(benchmark)
        and int(benchmark_summary.loc[0, "company_count"]) == benchmark["company_id"].nunique()
    )
    results.append(
        check(
            "company_benchmark_quality",
            benchmark_year_ok and benchmark_summary_ok,
            f"{len(benchmark)} company-year rows across {benchmark['company_id'].nunique()} companies",
        )
    )

    out_json = FINAL_DIR / "validation_results.json"
    out_csv = FINAL_DIR / "validation_summary.csv"
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    pd.DataFrame(results).to_csv(out_csv, index=False)

    failures = [item for item in results if not item["passed"]]
    print(f"Validation checks: {len(results) - len(failures)}/{len(results)} passed.")
    if failures:
        raise SystemExit(f"Validation failed: {failures}")


if __name__ == "__main__":
    main()

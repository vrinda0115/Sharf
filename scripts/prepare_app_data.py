"""Prepare validated SHARF data for the browser prototype.

The prototype is intentionally static so it can be opened directly from disk.
This script converts the validated final CSV outputs into a small JavaScript
data bundle consumed by UI/prototype/app.js.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL_DATA = ROOT / "data" / "final"
OUTPUT_DIR = ROOT / "UI" / "prototype" / "data"
OUTPUT_FILE = OUTPUT_DIR / "app_data.js"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(value: str) -> float:
    return round(float(value), 2)


def as_probability(value: str) -> float:
    return round(float(value), 3)


def latest_metrics_by_startup(metrics: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    for row in sorted(metrics, key=lambda item: (item["startup_id"], item["month"])):
        latest[row["startup_id"]] = row
    return latest


def validation_payload(validation_results: list[dict[str, str]]) -> dict[str, object]:
    passed = sum(1 for row in validation_results if str(row["passed"]).lower() == "true")
    return {
        "total_checks": len(validation_results),
        "passed_checks": passed,
        "all_passed": passed == len(validation_results),
        "checks": validation_results,
    }


def build_payload() -> dict[str, object]:
    profiles = read_csv(FINAL_DATA / "startup_profiles.csv")
    metrics = read_csv(FINAL_DATA / "sharf_monthly_metrics.csv")
    forecasts = read_csv(FINAL_DATA / "monte_carlo_risk_forecast.csv")
    validation_results = json.loads((FINAL_DATA / "validation_results.json").read_text(encoding="utf-8"))

    latest = latest_metrics_by_startup(metrics)
    forecast_by_id = {row["startup_id"]: row for row in forecasts}

    companies = []
    for profile in profiles:
        startup_id = profile["startup_id"]
        latest_row = latest[startup_id]
        forecast = forecast_by_id[startup_id]
        history = [
            {
                "month": row["month"],
                "sharf_score": as_float(row["sharf_score"]),
                "runway_months": as_float(row["runway_months"]),
                "monthly_revenue_usd": as_float(row["monthly_revenue_usd"]),
                "monthly_burn_usd": as_float(row["monthly_burn_usd"]),
            }
            for row in metrics
            if row["startup_id"] == startup_id
        ]

        companies.append(
            {
                "startup_id": startup_id,
                "startup_name": profile["startup_name"],
                "industry": profile["industry"],
                "stage": profile["stage"],
                "region": profile["region"],
                "founding_year": int(profile["founding_year"]),
                "risk_tier": latest_row["risk_tier"],
                "sharf_score": as_float(latest_row["sharf_score"]),
                "runway_months": as_float(latest_row["runway_months"]),
                "monthly_revenue_usd": as_float(latest_row["monthly_revenue_usd"]),
                "monthly_burn_usd": as_float(latest_row["monthly_burn_usd"]),
                "mom_revenue_growth": as_float(latest_row["mom_revenue_growth"]),
                "churn_rate": as_float(latest_row["monthly_churn_rate"]),
                "nps": as_float(latest_row["nps"]),
                "cac_payback_months": as_float(latest_row["cac_payback_months"]),
                "headcount": int(float(latest_row["headcount"])),
                "burn_recommendation": latest_row["burn_recommendation"],
                "fundraising_readiness": latest_row["fundraising_readiness"],
                "remediation_priority": latest_row["remediation_priority"],
                "forecast": {
                    "expected_score_6mo": as_float(forecast["expected_sharf_score_6mo"]),
                    "p10_runway_months_6mo": as_float(forecast["p10_runway_months_6mo"]),
                    "p50_runway_months_6mo": as_float(forecast["p50_runway_months_6mo"]),
                    "p90_runway_months_6mo": as_float(forecast["p90_runway_months_6mo"]),
                    "probability_cashout_6mo": as_probability(forecast["probability_cashout_6mo"]),
                    "probability_critical_risk_6mo": as_probability(forecast["probability_critical_risk_6mo"]),
                    "probability_runway_under_6mo": as_probability(forecast["probability_runway_under_6mo"]),
                    "risk_label": forecast["monte_carlo_risk_label"],
                    "simulation_count": int(forecast["simulation_count"]),
                },
                "history": history,
            }
        )

    risk_counts = Counter(company["risk_tier"] for company in companies)
    avg_score = round(sum(company["sharf_score"] for company in companies) / len(companies), 1)
    avg_runway = round(sum(company["runway_months"] for company in companies) / len(companies), 1)
    high_risk = sum(
        1
        for company in companies
        if company["risk_tier"] == "Critical" or company["forecast"]["probability_cashout_6mo"] >= 0.5
    )

    return {
        "meta": {
            "generated_from": [
                "data/final/startup_profiles.csv",
                "data/final/sharf_monthly_metrics.csv",
                "data/final/monte_carlo_risk_forecast.csv",
                "data/final/validation_results.json",
            ],
            "source_type": "validated synthetic startup-month data",
            "startup_count": len(companies),
            "observation_months": len({row["month"] for row in metrics}),
            "forecast_horizon_months": int(forecasts[0]["horizon_months"]),
            "validation": validation_payload(validation_results),
        },
        "portfolio": {
            "average_sharf_score": avg_score,
            "average_runway_months": avg_runway,
            "high_risk_count": high_risk,
            "risk_counts": dict(risk_counts),
        },
        "companies": sorted(companies, key=lambda item: item["sharf_score"]),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT_FILE.write_text(
        "window.SHARF_APP_DATA = "
        + json.dumps(payload, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INTERMEDIATE_DIR = ROOT / "data" / "intermediate"
FINAL_DIR = ROOT / "data" / "final"

SEED = 314
N_SIMULATIONS = 1000
HORIZON_MONTHS = 6


def load_benchmark_volatility() -> dict[str, float]:
    summary_path = FINAL_DIR / "company_benchmark_summary.csv"
    if not summary_path.exists():
        return {"employment_growth_spread": 0.08, "payroll_growth_spread": 0.10}
    summary = pd.read_csv(summary_path).iloc[0]
    employment_spread = float(summary["employment_growth_p90"] - summary["employment_growth_p10"]) / 2
    payroll_spread = float(summary["payroll_growth_p90"] - summary["payroll_growth_p10"]) / 2
    return {
        "employment_growth_spread": max(employment_spread, 0.05),
        "payroll_growth_spread": max(payroll_spread, 0.06),
    }


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def scaled(value: float, low: float, high: float, inverse: bool = False) -> float:
    score = 100 * (value - low) / (high - low)
    score = clamp(score, 0, 100)
    return 100 - score if inverse else score


def score_state(state: dict[str, float], governance_score: float) -> float:
    runway_score = scaled(state["runway_months"], 3, 18)
    revenue_score = scaled(state["mom_revenue_growth"], -0.08, 0.16)
    retention_score = scaled(state["monthly_churn_rate"], 0.0, 0.12, inverse=True)
    growth_efficiency_score = scaled(state["cac_payback_months"], 3, 24, inverse=True)
    sentiment_score = scaled(state["nps"], -20, 70)
    team_score = scaled(state["avg_time_to_fill_days"], 20, 90, inverse=True)
    return round(
        runway_score * 0.24
        + revenue_score * 0.18
        + retention_score * 0.16
        + growth_efficiency_score * 0.14
        + sentiment_score * 0.10
        + team_score * 0.08
        + governance_score * 0.10,
        1,
    )


def label_risk(prob_cashout: float, prob_critical: float, expected_score: float) -> str:
    if prob_cashout >= 0.35 or prob_critical >= 0.60:
        return "High forecast risk"
    if prob_cashout >= 0.15 or prob_critical >= 0.35 or expected_score < 60:
        return "Moderate forecast risk"
    return "Lower forecast risk"


def simulate_startup(
    startup_rows: pd.DataFrame,
    rng: np.random.Generator,
    benchmark_volatility: dict[str, float],
) -> tuple[pd.DataFrame, dict[str, float | str]]:
    rows = startup_rows.sort_values("month").copy()
    latest = rows.iloc[-1]
    history = rows.tail(6)

    growth_mu = float(history["mom_revenue_growth"].mean())
    growth_sigma = max(float(history["mom_revenue_growth"].std(ddof=0)), 0.035)
    churn_mu = float(history["monthly_churn_rate"].mean())
    churn_sigma = max(float(history["monthly_churn_rate"].std(ddof=0)), 0.012)
    burn_change = history["monthly_burn_usd"].pct_change().dropna()
    burn_mu = float(burn_change.mean()) if not burn_change.empty else 0.0
    benchmark_monthly_payroll_spread = benchmark_volatility["payroll_growth_spread"] / 12
    burn_sigma = max(float(burn_change.std(ddof=0)) if not burn_change.empty else 0.05, 0.04, benchmark_monthly_payroll_spread)
    cac_payback_mu = float(history["cac_payback_months"].mean())
    cac_payback_sigma = max(float(history["cac_payback_months"].std(ddof=0)), 2.0)
    nps_sigma = max(float(history["nps"].std(ddof=0)), 6.0)
    benchmark_monthly_employment_spread = benchmark_volatility["employment_growth_spread"] / 12
    fill_sigma = max(float(history["avg_time_to_fill_days"].std(ddof=0)), 7.0 + benchmark_monthly_employment_spread * 30)

    path_rows = []
    for simulation_id in range(1, N_SIMULATIONS + 1):
        revenue = float(latest["monthly_revenue_usd"])
        cash = float(latest["cash_balance_usd"])
        burn = float(latest["monthly_burn_usd"])
        min_runway = float(latest["runway_months"])
        final_state: dict[str, float] = {}

        for month_ahead in range(1, HORIZON_MONTHS + 1):
            growth = clamp(rng.normal(growth_mu, growth_sigma), -0.18, 0.25)
            revenue = max(500.0, revenue * (1 + growth))
            burn = max(10_000.0, burn * (1 + clamp(rng.normal(burn_mu, burn_sigma), -0.12, 0.18)))
            cash = max(0.0, cash - burn + revenue * rng.uniform(0.04, 0.16))
            runway = cash / burn if burn > 0 else 0.0
            min_runway = min(min_runway, runway)
            final_state = {
                "mom_revenue_growth": growth,
                "monthly_churn_rate": clamp(rng.normal(churn_mu - growth * 0.04, churn_sigma), 0.0, 0.22),
                "cac_payback_months": clamp(rng.normal(cac_payback_mu, cac_payback_sigma), 1.0, 60.0),
                "nps": clamp(rng.normal(float(latest["nps"]) + growth * 25, nps_sigma), -50.0, 90.0),
                "avg_time_to_fill_days": clamp(rng.normal(float(latest["avg_time_to_fill_days"]), fill_sigma), 18.0, 95.0),
                "runway_months": runway,
            }

        final_score = score_state(final_state, float(latest["governance_score"]))
        path_rows.append(
            {
                "startup_id": latest["startup_id"],
                "simulation_id": simulation_id,
                "horizon_months": HORIZON_MONTHS,
                "ending_cash_balance_usd": round(cash, 2),
                "ending_runway_months": round(final_state["runway_months"], 2),
                "minimum_runway_months": round(min_runway, 2),
                "ending_sharf_score": final_score,
                "cashout_flag": cash <= 0,
                "critical_risk_flag": final_score < 50,
            }
        )

    paths = pd.DataFrame(path_rows)
    summary = {
        "startup_id": latest["startup_id"],
        "forecast_start_month": latest["month"],
        "horizon_months": HORIZON_MONTHS,
        "simulation_count": N_SIMULATIONS,
        "baseline_sharf_score": round(float(latest["sharf_score"]), 1),
        "expected_sharf_score_6mo": round(float(paths["ending_sharf_score"].mean()), 1),
        "p10_runway_months_6mo": round(float(paths["ending_runway_months"].quantile(0.10)), 2),
        "p50_runway_months_6mo": round(float(paths["ending_runway_months"].quantile(0.50)), 2),
        "p90_runway_months_6mo": round(float(paths["ending_runway_months"].quantile(0.90)), 2),
        "probability_cashout_6mo": round(float(paths["cashout_flag"].mean()), 3),
        "probability_critical_risk_6mo": round(float(paths["critical_risk_flag"].mean()), 3),
        "probability_runway_under_6mo": round(float((paths["minimum_runway_months"] < 6).mean()), 3),
    }
    summary["monte_carlo_risk_label"] = label_risk(
        float(summary["probability_cashout_6mo"]),
        float(summary["probability_critical_risk_6mo"]),
        float(summary["expected_sharf_score_6mo"]),
    )
    return paths, summary


def main() -> None:
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(FINAL_DIR / "sharf_monthly_metrics.csv", parse_dates=["month"])
    rng = np.random.default_rng(SEED)
    benchmark_volatility = load_benchmark_volatility()

    all_paths = []
    summaries = []
    for _, group in metrics.groupby("startup_id", sort=True):
        paths, summary = simulate_startup(group, rng, benchmark_volatility)
        all_paths.append(paths)
        summaries.append(summary)

    path_df = pd.concat(all_paths, ignore_index=True)
    summary_df = pd.DataFrame(summaries)
    path_df.to_csv(INTERMEDIATE_DIR / "monte_carlo_simulation_paths.csv", index=False)
    summary_df.to_csv(FINAL_DIR / "monte_carlo_risk_forecast.csv", index=False)

    print(
        f"Wrote Monte Carlo forecast for {len(summary_df)} startups "
        f"using {N_SIMULATIONS} simulations each over {HORIZON_MONTHS} months."
    )


if __name__ == "__main__":
    main()

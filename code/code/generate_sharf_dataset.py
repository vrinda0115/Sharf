from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
INTERMEDIATE_DIR = ROOT / "data" / "intermediate"
FINAL_DIR = ROOT / "data" / "final"

SEED = 42
STARTUPS = 18
MONTHS = pd.period_range("2025-01", "2025-12", freq="M")


INDUSTRIES = ["SaaS", "Fintech", "Healthtech", "Edtech", "Marketplace", "Climate"]
STAGES = ["Pre-seed", "Seed", "Series A"]
REGIONS = ["US Midwest", "US Northeast", "US South", "US West"]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def scaled(value: float, low: float, high: float, inverse: bool = False) -> float:
    score = 100 * (value - low) / (high - low)
    score = clamp(score, 0, 100)
    return 100 - score if inverse else score


def make_profiles(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for idx in range(1, STARTUPS + 1):
        stage = rng.choice(STAGES, p=[0.25, 0.5, 0.25])
        industry = rng.choice(INDUSTRIES)
        rows.append(
            {
                "startup_id": f"ST{idx:03d}",
                "startup_name": f"SHARF Sample Venture {idx:02d}",
                "industry": industry,
                "stage": stage,
                "region": rng.choice(REGIONS),
                "founding_year": int(rng.integers(2020, 2025)),
                "board_or_advisory_group": bool(
                    rng.random() < {"Pre-seed": 0.25, "Seed": 0.55, "Series A": 0.85}[stage]
                ),
                "baseline_quality": float(rng.normal(0, 1)),
            }
        )
    return pd.DataFrame(rows)


def generate_monthly_snapshots(profiles: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for profile in profiles.itertuples(index=False):
        stage_factor = {"Pre-seed": 0.75, "Seed": 1.0, "Series A": 1.35}[profile.stage]
        quality = profile.baseline_quality
        revenue = max(8_000, rng.lognormal(mean=10.75, sigma=0.55) * stage_factor)
        cash = max(180_000, rng.lognormal(mean=13.95, sigma=0.62) * stage_factor)
        headcount = int(clamp(rng.normal(9 * stage_factor + quality * 1.5, 2.5), 3, 35))
        churn_anchor = clamp(rng.normal(0.055 - quality * 0.008, 0.025), 0.005, 0.16)
        cac_anchor = clamp(rng.normal(3_500 * stage_factor - quality * 200, 900), 800, 8_000)
        nps_anchor = clamp(rng.normal(35 + quality * 8, 18), -20, 80)

        for month_index, month in enumerate(MONTHS, start=1):
            macro_stress_index = round(0.55 + 0.05 * math.sin(month_index / 2), 3)
            growth = clamp(rng.normal(0.045 + quality * 0.012 - macro_stress_index * 0.01, 0.055), -0.12, 0.22)
            revenue = max(1_000, revenue * (1 + growth))
            burn = max(
                18_000,
                (28_000 * stage_factor)
                + headcount * rng.normal(5_600, 750)
                - revenue * rng.uniform(0.10, 0.24)
                + macro_stress_index * 7_500,
            )
            cash = max(0, cash - burn + revenue * rng.uniform(0.05, 0.18))
            churn = clamp(churn_anchor + rng.normal(0, 0.015) - growth * 0.05, 0, 0.22)
            cac = clamp(cac_anchor + rng.normal(0, 550) + macro_stress_index * 250, 500, 10_000)
            gross_margin = clamp(rng.normal(0.74, 0.08), 0.45, 0.9)
            new_arr = max(1, revenue * max(growth, 0.005) * 12)
            sales_marketing_spend = max(5_000, cac * rng.uniform(5, 22))
            cac_payback_months = clamp(cac / max((revenue / max(headcount, 1)) * gross_margin / 12, 1), 1, 60)
            nps = int(round(clamp(nps_anchor + rng.normal(0, 8) + growth * 30, -50, 90)))
            avg_time_to_fill_days = int(round(clamp(rng.normal(48 - quality * 4 + macro_stress_index * 10, 12), 18, 95)))
            if month_index in (4, 8):
                headcount = int(clamp(headcount + rng.integers(-1, 4), 3, 40))

            rows.append(
                {
                    "startup_id": profile.startup_id,
                    "month": month.to_timestamp().date().isoformat(),
                    "monthly_revenue_usd": round(revenue, 2),
                    "cash_balance_usd": round(cash, 2),
                    "monthly_burn_usd": round(burn, 2),
                    "monthly_churn_rate": round(churn, 4),
                    "customer_acquisition_cost_usd": round(cac, 2),
                    "sales_marketing_spend_usd": round(sales_marketing_spend, 2),
                    "new_arr_usd": round(new_arr, 2),
                    "gross_margin": round(gross_margin, 4),
                    "cac_payback_months": round(cac_payback_months, 2),
                    "nps": nps,
                    "headcount": headcount,
                    "avg_time_to_fill_days": avg_time_to_fill_days,
                    "macro_stress_index": macro_stress_index,
                }
            )
    return pd.DataFrame(rows)


def add_derived_metrics(snapshots: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    df = snapshots.sort_values(["startup_id", "month"]).copy()
    df["runway_months"] = (df["cash_balance_usd"] / df["monthly_burn_usd"]).round(2)
    df["mom_revenue_growth"] = df.groupby("startup_id")["monthly_revenue_usd"].pct_change().fillna(0).round(4)
    df["revenue_score"] = df["mom_revenue_growth"].apply(lambda x: scaled(x, -0.08, 0.16)).round(1)
    df["runway_score"] = df["runway_months"].apply(lambda x: scaled(x, 3, 18)).round(1)
    df["retention_score"] = df["monthly_churn_rate"].apply(lambda x: scaled(x, 0.0, 0.12, inverse=True)).round(1)
    df["growth_efficiency_score"] = df["cac_payback_months"].apply(lambda x: scaled(x, 3, 24, inverse=True)).round(1)
    df["customer_sentiment_score"] = df["nps"].apply(lambda x: scaled(x, -20, 70)).round(1)
    df["team_capacity_score"] = df["avg_time_to_fill_days"].apply(lambda x: scaled(x, 20, 90, inverse=True)).round(1)
    df = df.merge(profiles[["startup_id", "board_or_advisory_group", "stage", "industry", "region"]], on="startup_id", how="left")
    df["governance_score"] = np.where(df["board_or_advisory_group"], 100.0, 45.0)
    weights = {
        "runway_score": 0.24,
        "revenue_score": 0.18,
        "retention_score": 0.16,
        "growth_efficiency_score": 0.14,
        "customer_sentiment_score": 0.10,
        "team_capacity_score": 0.08,
        "governance_score": 0.10,
    }
    df["sharf_score"] = sum(df[col] * weight for col, weight in weights.items()).round(1)
    df["risk_tier"] = pd.cut(
        df["sharf_score"],
        bins=[-0.1, 49.9, 69.9, 100.0],
        labels=["Critical", "Watch", "Stable"],
    ).astype(str)
    df["burn_recommendation"] = np.select(
        [
            df["runway_months"] < 6,
            (df["runway_months"] < 12) | (df["mom_revenue_growth"] < 0),
        ],
        ["Reduce burn immediately", "Hold spend and review runway"],
        default="Maintain planned spend",
    )
    df["fundraising_readiness"] = np.select(
        [
            (df["sharf_score"] >= 75) & (df["runway_months"] >= 12) & (df["monthly_churn_rate"] <= 0.06),
            (df["sharf_score"] >= 60) & (df["runway_months"] >= 6),
        ],
        ["Ready for outreach", "Prepare for outreach"],
        default="Delay and fix blockers",
    )
    score_cols = [
        "runway_score",
        "revenue_score",
        "retention_score",
        "growth_efficiency_score",
        "customer_sentiment_score",
        "team_capacity_score",
        "governance_score",
    ]
    labels = {
        "runway_score": "Runway",
        "revenue_score": "Revenue growth",
        "retention_score": "Retention",
        "growth_efficiency_score": "Growth efficiency",
        "customer_sentiment_score": "Customer sentiment",
        "team_capacity_score": "Team capacity",
        "governance_score": "Governance",
    }
    df["remediation_priority"] = df[score_cols].idxmin(axis=1).map(labels)
    return df


def main() -> None:
    for directory in (RAW_DIR, INTERMEDIATE_DIR, FINAL_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    profiles = make_profiles(rng)
    raw_snapshots = generate_monthly_snapshots(profiles, rng)
    final_snapshots = add_derived_metrics(raw_snapshots, profiles)

    profiles.drop(columns=["baseline_quality"]).to_csv(RAW_DIR / "startup_profiles_raw.csv", index=False)
    raw_snapshots.to_csv(RAW_DIR / "monthly_snapshots_raw.csv", index=False)
    final_snapshots.to_csv(INTERMEDIATE_DIR / "monthly_snapshots_scored.csv", index=False)

    final_profiles = profiles.drop(columns=["baseline_quality"]).copy()
    final_profiles["profile_source"] = "synthetic_manual_constructed"
    final_profiles.to_csv(FINAL_DIR / "startup_profiles.csv", index=False)
    final_snapshots.to_csv(FINAL_DIR / "sharf_monthly_metrics.csv", index=False)

    data_dictionary = pd.DataFrame(
        [
            ("startup_id", "Unique synthetic startup identifier", "key"),
            ("month", "Monthly snapshot date at month start", "key/date"),
            ("monthly_revenue_usd", "Monthly recognized revenue in USD", "generated"),
            ("cash_balance_usd", "Cash available at month end in USD", "generated"),
            ("monthly_burn_usd", "Operating cash burn in USD", "generated"),
            ("monthly_churn_rate", "Monthly customer churn rate", "generated"),
            ("customer_acquisition_cost_usd", "Estimated customer acquisition cost in USD", "generated"),
            ("sales_marketing_spend_usd", "Monthly sales and marketing spend in USD", "generated"),
            ("new_arr_usd", "Estimated new annual recurring revenue added", "generated"),
            ("gross_margin", "Gross margin share used in payback estimation", "generated"),
            ("cac_payback_months", "Estimated CAC payback period", "derived/generated"),
            ("nps", "Net Promoter Score proxy", "generated"),
            ("headcount", "Employee headcount", "generated"),
            ("avg_time_to_fill_days", "Average hiring time-to-fill", "generated"),
            ("macro_stress_index", "Synthetic 0-1 external stress proxy", "generated"),
            ("runway_months", "Cash balance divided by monthly burn", "derived"),
            ("mom_revenue_growth", "Month-over-month revenue growth", "derived"),
            ("revenue_score", "Normalized 0-100 revenue trajectory score", "derived"),
            ("runway_score", "Normalized 0-100 runway score", "derived"),
            ("retention_score", "Normalized 0-100 churn/retention score", "derived"),
            ("growth_efficiency_score", "Normalized 0-100 CAC payback score", "derived"),
            ("customer_sentiment_score", "Normalized 0-100 NPS score", "derived"),
            ("team_capacity_score", "Normalized 0-100 hiring capacity score", "derived"),
            ("board_or_advisory_group", "Governance structure flag", "generated/manual"),
            ("stage", "Startup stage", "profile attribute"),
            ("industry", "Startup industry category", "profile attribute"),
            ("region", "Startup region category", "profile attribute"),
            ("governance_score", "Normalized score from governance flag", "derived"),
            ("sharf_score", "Weighted 0-100 composite health score", "derived"),
            ("risk_tier", "Critical, Watch, or Stable tier", "derived"),
            ("burn_recommendation", "Burn-rate decision recommendation", "derived"),
            ("fundraising_readiness", "Investor outreach timing recommendation", "derived"),
            ("remediation_priority", "Lowest-scoring operating dimension", "derived"),
        ],
        columns=["field_name", "definition", "field_type"],
    )
    data_dictionary.to_csv(FINAL_DIR / "data_dictionary.csv", index=False)

    print(f"Wrote {len(final_profiles)} startup profiles and {len(final_snapshots)} monthly metric rows.")


if __name__ == "__main__":
    main()

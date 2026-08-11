"""Quick exploratory analysis of SHARF final datasets."""
import pandas as pd
from pathlib import Path

base = Path(__file__).resolve().parent.parent / "data" / "final"

profiles = pd.read_csv(base / "startup_profiles.csv")
metrics = pd.read_csv(base / "sharf_monthly_metrics.csv")
forecast = pd.read_csv(base / "monte_carlo_risk_forecast.csv")
benchmark = pd.read_csv(base / "company_benchmark_summary.csv")

metrics["month"] = pd.to_datetime(metrics["month"])
latest = metrics.sort_values("month").groupby("startup_id").tail(1)

print("=== DATASET OVERVIEW ===")
print(f"Startups: {profiles.startup_id.nunique()}")
print(f"Monthly rows: {len(metrics)}")
print(f"Date range: {metrics.month.min().date()} to {metrics.month.max().date()}")
print(f"Industries: {sorted(profiles.industry.unique())}")
print(f"Stages: {sorted(profiles.stage.unique())}")

print("\n=== LATEST MONTH SHARF SCORES (Dec 2025) ===")
for _, r in latest.sort_values("sharf_score").iterrows():
    print(
        f"{r.startup_id}: SHARF={r.sharf_score:.1f}, tier={r.risk_tier}, "
        f"runway={r.runway_months:.1f}mo, remediation={r.remediation_priority}"
    )

print("\n=== RISK TIER DISTRIBUTION (latest month) ===")
print(latest["risk_tier"].value_counts().to_string())

print("\n=== SHARF SCORE SUMMARY (all months) ===")
print(metrics["sharf_score"].describe().round(2).to_string())

print("\n=== KEY METRICS CORRELATION WITH SHARF SCORE ===")
cols = [
    "sharf_score", "runway_months", "monthly_burn_usd", "monthly_revenue_usd",
    "monthly_churn_rate", "cac_payback_months", "nps", "mom_revenue_growth",
]
corr = metrics[cols].corr()["sharf_score"].drop("sharf_score").sort_values(key=abs, ascending=False)
for k, v in corr.items():
    print(f"  {k}: {v:.3f}")

print("\n=== MONTE CARLO FORECAST RISK ===")
for _, r in forecast.sort_values("probability_cashout_6mo", ascending=False).iterrows():
    print(
        f"{r.startup_id}: cashout={r.probability_cashout_6mo:.1%}, "
        f"critical={r.probability_critical_risk_6mo:.1%}, "
        f"label={r.monte_carlo_risk_label}, exp_sharf_6mo={r.expected_sharf_score_6mo:.1f}"
    )

print("\n=== TOP 5 LOWEST SHARF (latest) ===")
fc_map = forecast.set_index("startup_id")
prof_map = profiles.set_index("startup_id")
for _, r in latest.nsmallest(5, "sharf_score").iterrows():
    sid = r.startup_id
    f = fc_map.loc[sid]
    p = prof_map.loc[sid]
    print(
        f"{sid} ({p.industry}, {p.stage}): SHARF={r.sharf_score:.1f}, "
        f"runway={r.runway_months:.1f}mo, remediation={r.remediation_priority}, "
        f"6mo cashout={f.probability_cashout_6mo:.1%}"
    )

print("\n=== GOVERNANCE IMPACT (latest) ===")
gov = latest.merge(profiles[["startup_id", "board_or_advisory_group"]], on="startup_id")
print(gov.groupby("board_or_advisory_group")["sharf_score"].agg(["mean", "min", "max"]).round(1).to_string())

print("\n=== INDUSTRY / STAGE AVG SHARF (latest) ===")
merged = latest.merge(profiles[["startup_id", "industry", "stage"]], on="startup_id")
print(merged.groupby(["industry", "stage"])["sharf_score"].mean().round(1).to_string())

print("\n=== REMEDIATION PRIORITIES (latest) ===")
print(latest["remediation_priority"].value_counts().to_string())

print("\n=== BENCHMARK SUMMARY ===")
print(benchmark.to_string(index=False))

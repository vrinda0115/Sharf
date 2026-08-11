from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
FINAL_DIR = ROOT / "data" / "final"

RAW_PATH = RAW_DIR / "company_employment_payroll_raw.csv.gz"


def main() -> None:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Missing {RAW_PATH}. Place the user-provided BQ company employment/payroll CSV.GZ there."
        )

    df = pd.read_csv(RAW_PATH, compression="gzip")
    df = df.rename(
        columns={
            "BQ_COMPANY_NAME": "company_name",
            "BQ_EMPLOYMENT": "employment",
            "BQ_ID": "company_id",
            "BQ_PAYROLL": "payroll_usd",
            "BQ_WEBSITE": "website",
            "BQ_YEAR": "year",
        }
    )
    df["employment"] = pd.to_numeric(df["employment"], errors="coerce")
    df["payroll_usd"] = pd.to_numeric(df["payroll_usd"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    cleaned = df.dropna(subset=["company_id", "year"]).copy()
    cleaned = cleaned.sort_values(["company_id", "year"])
    cleaned["payroll_per_employee_usd"] = cleaned["payroll_usd"] / cleaned["employment"]
    cleaned.loc[~cleaned["payroll_per_employee_usd"].between(1_000, 1_000_000), "payroll_per_employee_usd"] = pd.NA
    cleaned["employment_growth"] = cleaned.groupby("company_id")["employment"].pct_change()
    cleaned["payroll_growth"] = cleaned.groupby("company_id")["payroll_usd"].pct_change()
    cleaned.loc[~cleaned["employment_growth"].between(-0.95, 5), "employment_growth"] = pd.NA
    cleaned.loc[~cleaned["payroll_growth"].between(-0.95, 5), "payroll_growth"] = pd.NA

    benchmark = cleaned[
        [
            "company_id",
            "company_name",
            "website",
            "year",
            "employment",
            "payroll_usd",
            "payroll_per_employee_usd",
            "employment_growth",
            "payroll_growth",
        ]
    ].copy()

    summary = pd.DataFrame(
        [
            {
                "benchmark_name": "company_employment_payroll",
                "source_file": str(RAW_PATH.relative_to(ROOT)),
                "row_count": len(benchmark),
                "company_count": benchmark["company_id"].nunique(),
                "year_min": int(benchmark["year"].min()),
                "year_max": int(benchmark["year"].max()),
                "employment_growth_p10": round(float(benchmark["employment_growth"].quantile(0.10)), 4),
                "employment_growth_p50": round(float(benchmark["employment_growth"].quantile(0.50)), 4),
                "employment_growth_p90": round(float(benchmark["employment_growth"].quantile(0.90)), 4),
                "payroll_growth_p10": round(float(benchmark["payroll_growth"].quantile(0.10)), 4),
                "payroll_growth_p50": round(float(benchmark["payroll_growth"].quantile(0.50)), 4),
                "payroll_growth_p90": round(float(benchmark["payroll_growth"].quantile(0.90)), 4),
                "payroll_per_employee_p50": round(float(benchmark["payroll_per_employee_usd"].quantile(0.50)), 2),
            }
        ]
    )

    benchmark.to_csv(FINAL_DIR / "company_employment_payroll_benchmark.csv", index=False)
    summary.to_csv(FINAL_DIR / "company_benchmark_summary.csv", index=False)
    print(
        f"Wrote benchmark data for {summary.loc[0, 'company_count']} companies "
        f"and {summary.loc[0, 'row_count']} company-year rows."
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "code" / script)], check=True)


def main() -> None:
    run("process_company_benchmarks.py")
    run("generate_sharf_dataset.py")
    run("monte_carlo_risk_forecast.py")
    run("train_runway_prediction_model.py")
    run("validate_sharf_dataset.py")


if __name__ == "__main__":
    main()

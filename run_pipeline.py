"""RetailPulse Pipeline Orchestrator — runs all steps in order with progress tracking"""
import sys
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

STEPS = [
    ("ETL Pipeline", "src.data.etl", False),
    ("Data Validation", "src.data.validation", True),
    ("RFM Features", "src.features.rfm", False),
    ("Customer Segmentation", "src.models.segmentation", False),
    ("Churn Prediction", "src.models.churn", False),
    ("Inventory Optimization", "src.models.inventory", False),
    ("Demand Forecasting", "src.models.forecasting", False),
    ("Accuracy Validation", "src.utils.validate", False),
]


def print_banner(text, char="="):
    print(f"\n{char * 60}")
    print(f"  {text}")
    print(f"{char * 60}")


def run_step(name, module, optional=False):
    print_banner(f"Running: {name}")
    start = time.time()

    cmd = [str(VENV_PYTHON), "-m", module]
    result = subprocess.run(cmd, capture_output=False, text=True, cwd=str(ROOT))

    duration = time.time() - start
    status = "PASS" if result.returncode == 0 else "FAIL"

    if result.returncode == 0:
        print(f"  -> {name}: {status} ({duration:.1f}s)")
    else:
        print(f"  -> {name}: {status} ({duration:.1f}s)")
        if optional:
            print(f"  (Optional step failed, continuing...)")
        else:
            print(f"  ERROR: Pipeline aborting at {name}")
            sys.exit(1)

    return status


def main():
    print_banner("RetailPulse Pipeline Orchestrator", "=")
    print(f"Python: {VENV_PYTHON}")
    print(f"Steps: {len(STEPS)}")
    print(f"{'=' * 60}")

    overall_start = time.time()
    passed = 0
    failed = 0

    for name, module, optional in STEPS:
        result = run_step(name, module, optional)
        if result == "PASS":
            passed += 1
        else:
            failed += 1

    total_duration = time.time() - overall_start
    print_banner("Pipeline Complete", "=")
    print(f"  Passed: {passed}/{len(STEPS)}")
    print(f"  Failed: {failed}/{len(STEPS)}")
    print(f"  Duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"{'=' * 60}")

    if failed > 0:
        print("\nSome steps failed. Check logs above.")
        sys.exit(1)
    print("\nAll pipeline steps completed successfully!")


if __name__ == "__main__":
    main()

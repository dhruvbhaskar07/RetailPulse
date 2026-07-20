"""RetailPulse Launcher — starts everything with one command"""
import sys
import time
import subprocess
import signal
import webbrowser
import logging
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_UVICORN = ROOT / ".venv" / "Scripts" / "uvicorn.exe"
VENV_STREAMLIT = ROOT / ".venv" / "Scripts" / "streamlit.exe"
API_PORT = 8000
DASH_PORT = 8501
LOG_FILE = ROOT / "launcher.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("launcher")

processes = []


def check_venv():
    if not VENV_PYTHON.exists():
        log.error("Virtual environment not found. Run: python setup.py")
        sys.exit(1)
    log.info("Virtual environment found")


def check_models():
    models_dir = ROOT / "data" / "processed" / "models"
    required = [
        models_dir / "kmeans_segmentation.pkl",
        models_dir / "churn_model.pkl",
        ROOT / "data" / "processed" / "inventory_recommendations.parquet",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        log.warning(f"Models missing: {len(missing)} — running pipeline...")
        for m in missing:
            log.info(f"  Missing: {m}")
        return False
    log.info("All models already trained")
    return True


def run_pipeline():
    log.info("=" * 50)
    log.info("Training pipeline started")
    log.info("=" * 50)

    steps = [
        ("ETL", "src.data.etl"),
        ("Segmentation", "src.models.segmentation"),
        ("Churn", "src.models.churn"),
        ("Inventory", "src.models.inventory"),
        ("Forecasting", "src.models.forecasting"),
    ]

    for name, module in steps:
        log.info(f"[{name}] Starting...")
        start = time.time()
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", module],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        duration = time.time() - start
        if result.returncode == 0:
            log.info(f"[{name}] Done ({duration:.1f}s)")
        else:
            log.warning(f"[{name}] Issues ({duration:.1f}s) — continuing")

    log.info("Pipeline complete")


def wait_for_health(url, service_name, timeout=30):
    import urllib.request
    log.info(f"Waiting for {service_name} at {url}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(url, timeout=3)
            if resp.status == 200:
                log.info(f"{service_name} is ready ({time.time()-start:.1f}s)")
                return True
        except Exception:
            pass
        time.sleep(1)
    log.warning(f"{service_name} did not respond within {timeout}s")
    return False


def cleanup(signum=None, frame=None):
    log.info("Shutting down...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    log.info("All services stopped")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    log.info("=" * 60)
    log.info("  RetailPulse Launcher")
    log.info("=" * 60)

    check_venv()

    if not check_models():
        run_pipeline()

    # Start API
    log.info(f"Starting API on port {API_PORT}...")
    api_proc = subprocess.Popen(
        [str(VENV_UVICORN), "src.api.main:app", "--host", "0.0.0.0", "--port", str(API_PORT)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    processes.append(api_proc)

    # Start Dashboard
    log.info(f"Starting Dashboard on port {DASH_PORT}...")
    dash_proc = subprocess.Popen(
        [str(VENV_STREAMLIT), "run", "src/dashboard/app.py", "--server.port", str(DASH_PORT)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    processes.append(dash_proc)

    # Wait for health
    api_ready = wait_for_health(f"http://localhost:{API_PORT}/health", "API")
    dash_ready = wait_for_health(f"http://localhost:{DASH_PORT}", "Dashboard", timeout=45)

    log.info("")
    log.info("=" * 60)
    log.info("  All services running!")
    log.info("=" * 60)
    log.info(f"  Dashboard:  http://localhost:{DASH_PORT}")
    log.info(f"  API Docs:   http://localhost:{API_PORT}/docs")
    log.info(f"  Health:     http://localhost:{API_PORT}/health")
    log.info("")
    log.info("  Login Credentials:")
    log.info("    Admin:   admin / admin123")
    log.info("    Analyst: analyst / analyst123")
    log.info("    Viewer:  viewer / viewer123")
    log.info("")
    log.info("  Press Ctrl+C to stop all services")
    log.info("=" * 60)

    # Open browser
    try:
        webbrowser.open(f"http://localhost:{DASH_PORT}")
    except Exception:
        pass

    # Keep running
    try:
        while True:
            time.sleep(1)
            if api_proc.poll() is not None:
                log.error("API process died unexpectedly")
                cleanup()
            if dash_proc.poll() is not None:
                log.error("Dashboard process died unexpectedly")
                cleanup()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()

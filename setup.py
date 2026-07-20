import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV_DIR = ROOT / ".venv"
PYTHON_VERSION = "python3.11"

def run(cmd, cwd=None):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)

def find_python311():
    """Find Python 3.11 executable"""
    import shutil
    for name in ["python3.11", "python3.11.exe", "python311"]:
        path = shutil.which(name)
        if path:
            return path
    # Try common Windows locations
    import os
    for base in [os.environ.get("LOCALAPPDATA", ""), os.environ.get("PROGRAMFILES", ""), "C:\\Python311"]:
        if base:
            candidates = [
                Path(base) / "python.exe",
                Path(base) / "python3.11.exe",
                Path(base) / "Python311" / "python.exe",
            ]
            for c in candidates:
                if c.exists():
                    try:
                        out = subprocess.check_output([str(c), "--version"], text=True)
                        if "3.11" in out:
                            return str(c)
                    except:
                        pass
    return sys.executable  # fallback

print("=" * 50)
print("Setting up RetailPulse environment (Python 3.11)")
print("=" * 50)

py311 = find_python311()
print(f"Found Python 3.11 at: {py311}")

if not VENV_DIR.exists():
    print(f"\nCreating virtual environment at {VENV_DIR}...")
    run(f'"{py311}" -m venv "{VENV_DIR}"')
else:
    print(f"\nVirtual environment already exists at {VENV_DIR}")

if sys.platform == "win32":
    pip = VENV_DIR / "Scripts" / "pip.exe"
    python = VENV_DIR / "Scripts" / "python.exe"
else:
    pip = VENV_DIR / "bin" / "pip"
    python = VENV_DIR / "bin" / "python"

print("\nUpgrading pip...")
run(f'"{pip}" install --upgrade pip')

print("\nInstalling requirements...")
run(f'"{pip}" install -r requirements.txt')

print("\nGenerating synthetic data...")
run(f'"{python}" -m src.data.generate')

print("\n" + "=" * 50)
print("Setup complete!")
print("=" * 50)
print(f"\nTo activate venv:")
print(f"  .\\.venv\\Scripts\\activate    (PowerShell)")
print(f"  source .venv/bin/activate    (bash)")
print(f"\nTo run data generation again:")
print(f"  python -m src.data.generate")
print(f"\nTo start MLflow UI:")
print(f"  mlflow ui --backend-store-uri file:./mlruns")
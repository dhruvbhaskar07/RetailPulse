"""API configuration — JWT, credentials, CORS, and external service URIs."""

import os
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import DATA_PROCESSED, MLRUNS_DIR

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY:
    key_file = Path(__file__).parent / ".jwt_secret"
    if key_file.exists():
        JWT_SECRET_KEY = key_file.read_text(encoding="utf-8").strip()
    else:
        import secrets
        JWT_SECRET_KEY = secrets.token_urlsafe(32)
        key_file.write_text(JWT_SECRET_KEY, encoding="utf-8")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
ANALYST_USERNAME = os.getenv("ANALYST_USERNAME", "analyst")
ANALYST_PASSWORD_HASH = os.getenv("ANALYST_PASSWORD_HASH", "")
VIEWER_USERNAME = os.getenv("VIEWER_USERNAME", "viewer")
VIEWER_PASSWORD_HASH = os.getenv("VIEWER_PASSWORD_HASH", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_PROCESSED / 'audit.db'}")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(",")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{MLRUNS_DIR / 'mlflow.db'}")

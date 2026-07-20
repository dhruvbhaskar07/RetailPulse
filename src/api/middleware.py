"""FastAPI middleware for Prometheus metrics collection and audit logging."""

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from src.api.services.audit_service import log_audit_entry

REQUEST_COUNT = Counter("retailpulse_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("retailpulse_request_duration_seconds", "Request latency", ["method", "endpoint"])
ACTIVE_CONNECTIONS = Gauge("retailpulse_active_connections", "Active connections")

SKIP_PATHS = {"/health", "/health/ready", "/health/live", "/metrics", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    ACTIVE_CONNECTIONS.inc()
    try:
        response = await call_next(request)
        return response
    finally:
        ACTIVE_CONNECTIONS.dec()
        if request.url.path not in SKIP_PATHS:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
            REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)

async def audit_middleware(request: Request, call_next):
    if request.url.path in SKIP_PATHS:
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    user_id = "anonymous"
    user_role = "none"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from src.api.auth.jwt import decode_token
            payload = decode_token(auth_header.split(" ")[1])
            user_id = payload.get("sub", "anonymous")
            roles = payload.get("roles", [])
            user_role = roles[0] if roles else "none"
        except Exception:
            pass

    log_audit_entry(
        user_id=user_id, user_role=user_role,
        action=request.method, endpoint=request.url.path,
        method=request.method,
        ip_address=request.client.host if request.client else "unknown",
        status_code=response.status_code, duration_ms=duration_ms,
    )

    return response

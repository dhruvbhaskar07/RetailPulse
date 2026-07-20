"""Auth dependencies — token verification, role enforcement, user extraction, and rate limiting."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import time

security = HTTPBearer()
TOKEN_BLACKLIST: set = set()

_request_timestamps: dict = {}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    if token in TOKEN_BLACKLIST:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    from src.api.auth.jwt import decode_token
    return decode_token(token)

def get_current_user(payload: dict = Depends(verify_token)) -> dict:
    return payload

def require_role(roles: List[str]):
    def checker(user: dict = Depends(get_current_user)):
        user_roles = user.get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires one of roles: {roles}")
        return user
    return checker

def rate_limit_by_user(request: Request, max_requests: int = 60, window_seconds: int = 60):
    user_id = "anonymous"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from src.api.auth.jwt import decode_token
            payload = decode_token(token)
            user_id = payload.get("sub", "anonymous")
        except Exception:
            pass
    key = f"{user_id}:{request.url.path}"
    now = time.time()
    timestamps = _request_timestamps.get(key, [])
    timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(timestamps) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    timestamps.append(now)
    _request_timestamps[key] = timestamps

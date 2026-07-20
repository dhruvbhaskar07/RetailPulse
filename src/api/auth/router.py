"""Auth router — login, logout, and refresh endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from src.api.auth.jwt import authenticate_user, create_access_token, hash_password, init_users
from src.api.auth.dependencies import security, verify_token, TOKEN_BLACKLIST
from src.api.schemas.request import LoginRequest
from src.api.schemas.response import TokenResponse
from src.api.config import ACCESS_TOKEN_EXPIRE_MINUTES, ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ANALYST_USERNAME, ANALYST_PASSWORD_HASH, VIEWER_USERNAME, VIEWER_PASSWORD_HASH
from src.api.services.audit_service import log_audit_entry

router = APIRouter(tags=["auth"])

def setup_default_users():
    users = {}
    if ADMIN_PASSWORD_HASH:
        users[ADMIN_USERNAME] = {"password": ADMIN_PASSWORD_HASH, "role": "admin", "name": "Admin User"}
    else:
        users[ADMIN_USERNAME] = {"password": hash_password("admin123"), "role": "admin", "name": "Admin User"}
    if ANALYST_PASSWORD_HASH:
        users[ANALYST_USERNAME] = {"password": ANALYST_PASSWORD_HASH, "role": "analyst", "name": "Analyst User"}
    else:
        users[ANALYST_USERNAME] = {"password": hash_password("analyst123"), "role": "analyst", "name": "Analyst User"}
    if VIEWER_PASSWORD_HASH:
        users[VIEWER_USERNAME] = {"password": VIEWER_PASSWORD_HASH, "role": "viewer", "name": "Viewer User"}
    else:
        users[VIEWER_USERNAME] = {"password": hash_password("viewer123"), "role": "viewer", "name": "Viewer User"}
    init_users(users)

@router.post("/auth/login", response_model=TokenResponse)
async def login(request: Request, login_data: LoginRequest):
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(
        data={"sub": login_data.username, "roles": [user["role"]], "name": user.get("name", login_data.username)}
    )
    return TokenResponse(access_token=token)

@router.post("/auth/logout")
async def logout(credentials=Depends(security)):
    TOKEN_BLACKLIST.add(credentials.credentials)
    return {"message": "Logged out successfully"}

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(payload: dict = Depends(verify_token)):
    user_id = payload.get("sub")
    roles = payload.get("roles", ["user"])
    token = create_access_token(data={"sub": user_id, "roles": roles})
    return TokenResponse(access_token=token)

"""Authentication package — JWT creation, validation, and role-based access controls."""

from src.api.auth.jwt import create_access_token, decode_token, authenticate_user, hash_password, verify_password, init_users
from src.api.auth.dependencies import verify_token, get_current_user, require_role, rate_limit_by_user, security, TOKEN_BLACKLIST

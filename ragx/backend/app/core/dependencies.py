from fastapi import Header, HTTPException, Depends
from typing import Optional
from app.services.auth_service import AuthService

async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Extracts Bearer token from Authorization header if present and returns user info.
    Does not raise exception if token is missing.
    """
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return AuthService.validate_session(token)

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Strict server-side authentication dependency.
    Raises HTTP 401 Unauthorized if token is missing, invalid, or expired.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication token required.")
    token = authorization.replace("Bearer ", "").strip()
    user = AuthService.validate_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token. Please log in again.")
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Strict server-side authorization dependency for Admin endpoints.
    Raises HTTP 403 Forbidden if authenticated user does not have ADMIN role.
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Administrative privileges required.")
    return current_user

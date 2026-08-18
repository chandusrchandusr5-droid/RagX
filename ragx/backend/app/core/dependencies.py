from fastapi import Header, Query, HTTPException, Depends
from typing import Optional
from app.services.auth_service import AuthService

async def get_optional_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Optional[dict]:
    """
    Extracts Bearer token from Authorization header or ?token= query parameter if present.
    Returns authenticated user dict or None if unauthenticated.
    """
    tok = None
    if authorization and authorization.startswith("Bearer "):
        tok = authorization.replace("Bearer ", "").strip()
    elif token:
        tok = token.strip()

    if not tok:
        return None
    return AuthService.validate_session(tok)

async def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> dict:
    """
    Strict server-side authentication dependency.
    Raises HTTP 401 Unauthorized if token is missing, invalid, or expired.
    """
    user = await get_optional_user(authorization=authorization, token=token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication token required or expired. Please log in.")
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Strict server-side authorization dependency for Admin endpoints.
    Raises HTTP 403 Forbidden if authenticated user does not have ADMIN role.
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Administrative privileges required.")
    return current_user

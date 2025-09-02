from enum import Enum
from fastapi import Header, HTTPException, status, Depends
from typing import Optional
from backend.app.core.security import decode_jwt

class Role(str, Enum):
    admin = "admin"
    legal = "legal"
    risk = "risk"
    viewer = "viewer"

def get_role(
    authorization: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> Role:
    # Prefer explicit header for quick local testing
    if x_user_role:
        try:
            return Role(x_user_role)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role header")
    # Otherwise, try JWT bearer
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        claims = decode_jwt(token)
        role = claims.get("role", "viewer")
        return Role(role)
    return Role.viewer

RequireViewer = Depends(get_role)

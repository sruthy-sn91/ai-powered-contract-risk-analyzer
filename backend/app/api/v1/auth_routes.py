from fastapi import APIRouter, Body
from backend.app.core.security import encode_jwt

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=dict)
def login(username: str = Body(..., embed=True), password: str = Body(..., embed=True), role: str = Body("viewer", embed=True)):
    # Local stub: accept any user/pass and return a JWT (DO NOT use in production)
    token = encode_jwt(sub=username, exp_seconds=3600)
    return {"access_token": token, "token_type": "bearer", "role": role}

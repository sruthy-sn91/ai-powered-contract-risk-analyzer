import time
import jwt
from backend.app.core.config import settings

def encode_jwt(sub: str, exp_seconds: int = 3600) -> str:
    payload = {"sub": sub, "exp": int(time.time()) + exp_seconds}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])

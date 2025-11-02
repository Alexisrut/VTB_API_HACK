from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import get_settings

settings = get_settings()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int) -> str:
    data = {
        "sub": str(user_id),
        "type": "refresh"
    }
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token(data, expires_delta)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def decode_token(token: str) -> Optional[int]:
    payload = verify_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            return int(user_id)
    return None

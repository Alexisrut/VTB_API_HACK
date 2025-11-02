from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from app.security.jwt_handler import decode_token

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> int:
    token = credentials.credentials
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user_id

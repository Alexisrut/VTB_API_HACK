from pydantic_settings import BaseSettings
from typing import Optional
import uuid
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fastapi_user:fastapi_password@localhost:5432/fastapi_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "aMeucfHi2Xxl3v0LYb1Tcduk-NuQOOjGVrTxqhDrT0A"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # SMS
    SMS_SERVICE_PROVIDER: str = "sms_ru"
    SMS_API_KEY: uuid.UUID = uuid.UUID("18608A37-567C-3C70-F128-03938B6AF52A")
    SMS_FROM_NAME: str = "YourApp"
    
    # OAuth2
    BANK_API_URL: str = "https://vbank.open.bankingapi.ru"
    BANK_CLIENT_ID: str = "team261"
    BANK_CLIENT_SECRET: str = "gBRvg9R6lYhvWHAOQFOH1HGarl1q80Rt"
   # BANK_REDIRECT_URI: str
    '''
    # Frontend
    FRONTEND_URL: str
    '''
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

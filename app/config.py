from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # SMS
    SMS_SERVICE_PROVIDER: str = "sms_ru"
    SMS_API_KEY: str
    SMS_FROM_NAME: str = "YourApp"
    
    # OAuth2
    BANK_API_URL: str
    BANK_CLIENT_ID: str
    BANK_CLIENT_SECRET: str
    BANK_REDIRECT_URI: str
    
    # Email
    SMTP_SERVER: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    
    # Frontend
    FRONTEND_URL: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

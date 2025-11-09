from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict

class BankConfig(BaseSettings):
    api_url: str
    client_id: str
    client_secret: str
    requesting_bank: str
    requesting_bank_name: str
    redirecting_url: str


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
    SMS_API_KEY: str = "18608A37-567C-3C70-F128-03938B6AF52A"
    SMS_FROM_NAME: str = "YourApp"
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    
    # ==================== КОНФИГУРАЦИЯ ДЛЯ ТРЁХ БАНКОВ ====================
    
    # Virtual Bank (vbank)
    VBANK_API_URL: str = "https://vbank.open.bankingapi.ru"
    VBANK_CLIENT_ID: str = "team261-1"
    VBANK_CLIENT_SECRET: str = "gBRvg9R6lYhvWHAOQFOH1HGarl1q80Rt"
    VBANK_REQUESTING_BANK: str = "team261"
    VBANK_REQUESTING_BANK_NAME: str = "Team 200 Virtual Bank App"
    VBANK_REDIRECTING_URL: str = "https://vbank.open.bankingapi.ru/client/"
    
    # Awesome Bank (abank)
    ABANK_API_URL: str = "https://abank.open.bankingapi.ru"
    ABANK_CLIENT_ID: str = "team261-1"
    ABANK_CLIENT_SECRET: str = "gBRvg9R6lYhvWHAOQFOH1HGarl1q80Rt"
    ABANK_REQUESTING_BANK: str = "team261"
    ABANK_REQUESTING_BANK_NAME: str = "Team 200 Awesome Bank App"
    ABANK_REDIRECTING_URL: str = "https://abank.open.bankingapi.ru/client/"
    
    # Smart Bank (sbank)
    SBANK_API_URL: str = "https://sbank.open.bankingapi.ru"
    SBANK_CLIENT_ID: str = "team261-1"
    SBANK_CLIENT_SECRET: str = "gBRvg9R6lYhvWHAOQFOH1HGarl1q80Rt"
    SBANK_REQUESTING_BANK: str = "team261"
    SBANK_REQUESTING_BANK_NAME: str = "Team 200 Smart Bank App"
    SBANK_REDIRECTING_URL: str = "https://sbank.open.bankingapi.ru/client/"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_bank_config(self, bank_code: str) -> BankConfig:
        """
        Получить конфигурацию для конкретного банка
        
        Args:
            bank_code: Код банка ('vbank', 'abank', 'sbank')
        
        Returns:
            BankConfig с параметрами банка
        
        Raises:
            ValueError: Если банк не найден
        """
        bank_configs = {
            "vbank": BankConfig(
                api_url=self.VBANK_API_URL,
                client_id=self.VBANK_CLIENT_ID,
                client_secret=self.VBANK_CLIENT_SECRET,
                requesting_bank=self.VBANK_REQUESTING_BANK,
                requesting_bank_name=self.VBANK_REQUESTING_BANK_NAME,
                redirecting_url=self.VBANK_REDIRECTING_URL
            ),
            "abank": BankConfig(
                api_url=self.ABANK_API_URL,
                client_id=self.ABANK_CLIENT_ID,
                client_secret=self.ABANK_CLIENT_SECRET,
                requesting_bank=self.ABANK_REQUESTING_BANK,
                requesting_bank_name=self.ABANK_REQUESTING_BANK_NAME,
                redirecting_url=self.ABANK_REDIRECTING_URL
            ),
            "sbank": BankConfig(
                api_url=self.SBANK_API_URL,
                client_id=self.SBANK_CLIENT_ID,
                client_secret=self.SBANK_CLIENT_SECRET,
                requesting_bank=self.SBANK_REQUESTING_BANK,
                requesting_bank_name=self.SBANK_REQUESTING_BANK_NAME,
                redirecting_url=self.SBANK_REDIRECTING_URL
            )
        }
        
        if bank_code not in bank_configs:
            raise ValueError(f"Unknown bank code: {bank_code}. Available: {list(bank_configs.keys())}")
        
        return bank_configs[bank_code]
    
    def get_all_banks(self) -> Dict[str, BankConfig]:
        """Получить конфигурации всех банков"""
        return {
            "vbank": self.get_bank_config("vbank"),
            "abank": self.get_bank_config("abank"),
            "sbank": self.get_bank_config("sbank")
        }

@lru_cache()
def get_settings():
    return Settings()
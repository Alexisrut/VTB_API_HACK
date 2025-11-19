from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    FRONTEND_URL: str = "https://potential-halibut-6x6jgqgvgpxh5q6x-5173.app.github.dev"
    CORS_ORIGINS: str = ""  # Comma-separated list of additional CORS origins
    
    # ==================== КОНФИГУРАЦИЯ ДЛЯ ТРЁХ БАНКОВ ====================
    
    # Virtual Bank (vbank)
    VBANK_API_URL: str = "https://vbank.open.bankingapi.ru"
    VBANK_CLIENT_ID: str = "team261-3"
    VBANK_CLIENT_SECRET: str = "24ADfpV1IyoAAP7d"
    VBANK_REQUESTING_BANK: str = "team261"
    VBANK_REQUESTING_BANK_NAME: str = "Team 261 Virtual Bank App"
    VBANK_REDIRECTING_URL: str = "https://vbank.open.bankingapi.ru/client/"
    
    # Awesome Bank (abank)
    ABANK_API_URL: str = "https://abank.open.bankingapi.ru"
    ABANK_CLIENT_ID: str = "team261-3"
    ABANK_CLIENT_SECRET: str = "24ADfpV1IyoAAP7d"
    ABANK_REQUESTING_BANK: str = "team261"
    ABANK_REQUESTING_BANK_NAME: str = "Team 261 Awesome Bank App"
    ABANK_REDIRECTING_URL: str = "https://abank.open.bankingapi.ru/client/"
    
    # Smart Bank (sbank)
    SBANK_API_URL: str = "https://sbank.open.bankingapi.ru"
    SBANK_CLIENT_ID: str = "team261-3"
    SBANK_CLIENT_SECRET: str = "24ADfpV1IyoAAP7d"
    SBANK_REQUESTING_BANK: str = "team261"
    SBANK_REQUESTING_BANK_NAME: str = "Team 261 Smart Bank App"
    SBANK_REDIRECTING_URL: str = "https://sbank.open.bankingapi.ru/client/"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    async def get_bank_config(self, bank_code: str, db: Optional[AsyncSession] = None) -> BankConfig:
        """
        Получить конфигурацию для конкретного банка
        Сначала проверяет базу данных, затем fallback на env переменные
        
        Args:
            bank_code: Код банка (любой, не только vbank, abank, sbank)
            db: Database session (опционально, для проверки БД)
        
        Returns:
            BankConfig с параметрами банка
        
        Raises:
            ValueError: Если банк не найден
        """
        # Сначала проверяем базу данных
        if db:
            try:
                from app.models import BankConfigModel
                result = await db.execute(
                    select(BankConfigModel).where(
                        BankConfigModel.bank_code == bank_code,
                        BankConfigModel.is_active == True
                    )
                )
                db_config = result.scalar_one_or_none()
                if db_config:
                    return BankConfig(
                        api_url=db_config.api_url,
                        client_id=db_config.client_id,
                        client_secret=db_config.client_secret,
                        requesting_bank=db_config.requesting_bank,
                        requesting_bank_name=db_config.requesting_bank_name,
                        redirecting_url=db_config.redirecting_url
                    )
            except Exception as e:
                # Если ошибка при работе с БД, продолжаем с env fallback
                pass
        
        # Fallback на env переменные для стандартных банков
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
        
        if bank_code in bank_configs:
            return bank_configs[bank_code]
        
        raise ValueError(f"Unknown bank code: {bank_code}. Bank not found in database or environment variables. Please add the bank configuration first.")
    
    async def get_all_banks(self, db: Optional[AsyncSession] = None) -> Dict[str, BankConfig]:
        """Получить конфигурации всех банков (из БД и env)"""
        banks = {}
        
        # Получаем банки из БД
        if db:
            try:
                from app.models import BankConfigModel
                result = await db.execute(
                    select(BankConfigModel).where(BankConfigModel.is_active == True)
                )
                db_configs = result.scalars().all()
                for db_config in db_configs:
                    banks[db_config.bank_code] = BankConfig(
                        api_url=db_config.api_url,
                        client_id=db_config.client_id,
                        client_secret=db_config.client_secret,
                        requesting_bank=db_config.requesting_bank,
                        requesting_bank_name=db_config.requesting_bank_name,
                        redirecting_url=db_config.redirecting_url
                    )
            except Exception:
                pass
        
        # Добавляем стандартные банки из env (если их еще нет)
        for bank_code in ["vbank", "abank", "sbank"]:
            if bank_code not in banks:
                try:
                    banks[bank_code] = await self.get_bank_config(bank_code, db=None)
                except ValueError:
                    pass
        
        return banks

@lru_cache()
def get_settings():
    return Settings()
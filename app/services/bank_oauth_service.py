import aiohttp
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models import OAuthSession, User
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class OAuth2BankService:
    def __init__(self):
        self.bank_api_url = settings.BANK_API_URL
        self.client_id = settings.BANK_CLIENT_ID
        self.client_secret = settings.BANK_CLIENT_SECRET
        self.requesting_bank = "team261"  # Или из конфига
        self.requesting_bank_name = "team261 App"
    
    # ============ ШАГ 1: Получение токена банка ============
    async def get_bank_access_token(self) -> str:
        """
        Получить access token банка для доступа к данным клиентов
        
        POST https://vbank.open.bankingapi.ru/auth/bank-token
        ?client_id=team200&client_secret=YOUR_SECRET
        
        Returns:
            str: access_token для использования в дальнейших запросах
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.bank_api_url}/auth/bank-token"
                params = {
                    "client_id": self.requesting_bank,
                    "client_secret": self.client_secret
                }
                
                logger.info(f"Getting bank token from {url}")
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        access_token = data.get("access_token")
                        logger.info("Successfully obtained bank access token")
                        return access_token
                    else:
                        error_text = await resp.text()
                        logger.error(f"Failed to get bank token: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting bank token: {e}")
            return None
    
    # ============ ШАГ 2: Запрос согласия (авто-одобрение) ============
    async def request_account_consent(self, access_token: str, user_id: str) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.bank_api_url}/account-consents/request"
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": self.requesting_bank,
                    "Content-Type": "application/json"
                }
                
                body = {
                    "client_id": f"{user_id}",
                    "permissions": ["ReadAccountsDetail", "ReadBalances"],
                    "reason": "Агрегация счетов для HackAPI",
                    "requesting_bank": self.requesting_bank,
                    "requesting_bank_name": self.requesting_bank_name
                }
                
                logger.info(f"Requesting account consent for user {user_id}")
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"Consent received: {data.get('consent_id')}")
                        return {
                            "status": data.get("status", "approved"),
                            "consent_id": data.get("consent_id"),
                            "auto_approved": data.get("auto_approved", True)
                        }
                    else:
                        error_text = await resp.text()
                        logger.error(f"Failed to request consent {user_id}: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error requesting consent: {e}")
            return None
    
    # ============ ШАГ 3: Получить данные счетов ============
    async def get_user_accounts(self, access_token: str, user_id: str, consent_id: str) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.bank_api_url}/accounts"
                
                params = {
                    "client_id": f"{user_id}"
                }
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": self.requesting_bank,
                    "X-Consent-Id": consent_id,
                    "Accept": "application/json"
                }
                
                logger.info(f"Fetching accounts for user {user_id}")
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"Successfully fetched {len(data.get('accounts', []))} accounts")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"Failed to fetch accounts: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            return None

    async def get_bank_accounts_full_cycle(self, user_id: str) -> dict:
        try:
            # ШАГ 1: Получить токен банка
            logger.info("STEP 1: Getting bank access token...")
            access_token = await self.get_bank_access_token()
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Failed to obtain bank access token"
                }
            
            # ШАГ 2: Запросить согласие
            logger.info("STEP 2: Requesting account consent...")
            consent_data = await self.request_account_consent(access_token, self.client_id)
            
            if not consent_data:
                return {
                    "success": False,
                    "error": "Failed to request account consent"
                }
            
            consent_id = consent_data.get("consent_id")

            logger.info("STEP 3: Fetching user accounts...")
            accounts_data = await self.get_user_accounts(access_token, self.client_id, consent_id)
            
            if not accounts_data:
                return {
                    "success": False,
                    "error": "Failed to fetch accounts"
                }
            print(accounts_data)
            return {
                "success": True,
                "bills": accounts_data['data']['account'],
                "consent_id": consent_id,
                "auto_approved": consent_data.get("auto_approved", True)
            }
        
        except Exception as e:
            logger.error(f"Error in full cycle: {e}")
            return {
                "success": False,
                "error": str(e)
            }
oauth_bank_service = OAuth2BankService()
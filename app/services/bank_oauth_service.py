import aiohttp
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict
from app.config import get_settings
from app.models import OAuthSession, User
import logging


settings = get_settings()
logger = logging.getLogger(__name__)


class OAuth2BankService:
    """
    Универсальный сервис для работы с банковским API для трёх банков.
    Поддерживает: vbank, abank, sbank
    
    Usage:
        service = OAuth2BankService(bank_code="vbank")
        result = await service.get_bank_accounts_full_cycle(user_id="123")
    """
    
    def __init__(self, bank_code: str):
        """
        Инициализация сервиса для конкретного банка
        
        Args:
            bank_code: Код банка ('vbank', 'abank', 'sbank')
        
        Raises:
            ValueError: Если bank_code неизвестен
        """
        # Получаем конфигурацию для выбранного банка
        self.bank_code = bank_code
        bank_config = settings.get_bank_config(bank_code)
        
        # Устанавливаем параметры из конфигурации
        self.bank_api_url = bank_config.api_url
        self.client_id = bank_config.client_id
        self.client_secret = bank_config.client_secret
        self.requesting_bank = bank_config.requesting_bank
        self.requesting_bank_name = bank_config.requesting_bank_name
        self.redirecting_url = bank_config.redirecting_url
        
        
        logger.info(f"[{self.bank_code}] Initialized OAuth2BankService with URL: {self.bank_api_url}")
    
    # ============ ШАГ 1: Получение токена банка ============
    async def get_bank_access_token(self) -> Optional[str]:
        """
        Получить access token банка для доступа к данным клиентов
        
        POST https://{bank}.open.bankingapi.ru/auth/bank-token
        ?client_id=team261&client_secret=YOUR_SECRET
        
        Returns:
            str: access_token для использования в дальнейших запросах
            None: При ошибке
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.bank_api_url}/auth/bank-token"
                params = {
                    "client_id": self.requesting_bank,
                    "client_secret": self.client_secret
                }
                
                logger.info(f"[{self.bank_code}] Getting bank token from {url}")
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        access_token = data.get("access_token")
                        logger.info(f"[{self.bank_code}] Successfully obtained bank access token")
                        return access_token
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{self.bank_code}] Failed to get bank token: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{self.bank_code}] Error getting bank token: {e}")
            return None
    
    # ============ ШАГ 2: Запрос согласия (авто-одобрение) ============
    async def request_account_consent(self, access_token: str, user_id: str) -> Optional[Dict]:
        """
        Запросить согласие на доступ к счетам пользователя
        
        POST https://{bank}.open.bankingapi.ru/account-consents/request
        
        Args:
            access_token: Токен банка (из шага 1)
            user_id: ID пользователя
        
        Returns:
            dict: {"status": "approved", "consent_id": "...", "auto_approved": true}
            None: При ошибке
        """
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
                
                logger.info(f"[{self.bank_code}] Requesting account consent for user {user_id}")
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        consent_id = data.get("consent_id")
                        logger.info(f"[{self.bank_code}] Consent received: {consent_id}")
                        return {
                            "status": data.get("status", "approved"),
                            "consent_id": consent_id,
                            "auto_approved": data.get("auto_approved", True)
                        }
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{self.bank_code}] Failed to request consent for user {user_id}: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{self.bank_code}] Error requesting consent: {e}")
            return None
    
    # ============ ШАГ 3: Получить данные счетов ============
    async def get_user_accounts(self, access_token: str, user_id: str, consent_id: str) -> Optional[Dict]:
        """
        Получить список счетов пользователя
        
        GET https://{bank}.open.bankingapi.ru/accounts?client_id={user_id}
        
        Args:
            access_token: Токен банка
            user_id: ID пользователя
            consent_id: ID согласия (из шага 2)
        
        Returns:
            dict: {"accounts": [...]} или {"data": {"account": [...]}}
            None: При ошибке
        """
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
                
                logger.info(f"[{self.bank_code}] Fetching accounts for user {user_id}")
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Поддержка разных форматов ответа
                        if 'data' in data and 'account' in data['data']:
                            accounts = data['data']['account']
                        elif 'accounts' in data:
                            accounts = data['accounts']
                        else:
                            accounts = []
                        
                        logger.info(f"[{self.bank_code}] Successfully fetched {len(accounts)} accounts")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{self.bank_code}] Failed to fetch accounts: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{self.bank_code}] Error fetching accounts: {e}")
            return None
    
    # ============ КОМПЛЕКСНЫЙ МЕТОД: Полный цикл ============
    async def get_bank_accounts_full_cycle(self, user_id: str) -> Dict:
        """
        Выполнить полный цикл получения счетов пользователя:
        1. Получить access token банка
        2. Запросить согласие
        3. Получить данные счетов
        
        Args:
            user_id: ID пользователя
        
        Returns:
            dict: {
                "success": True/False,
                "bank_code": "vbank",
                "bills": [...],  # Список счетов
                "consent_id": "...",
                "auto_approved": True/False,
                "error": "..." (если есть)
            }
        """
        try:
            logger.info(f"[{self.bank_code}] ===== STARTING FULL CYCLE for user {user_id} =====")
            
            # ШАГ 1: Получить токен банка
            logger.info(f"[{self.bank_code}] STEP 1: Getting bank access token...")
            access_token = await self.get_bank_access_token()
            
            if not access_token:
                logger.error(f"[{self.bank_code}] STEP 1 FAILED: No access token")
                return {
                    "success": False,
                    "bank_code": self.bank_code,
                    "error": "Failed to obtain bank access token"
                }
            
            logger.info(f"[{self.bank_code}] STEP 1 SUCCESS: Access token obtained")
            
            # ШАГ 2: Запросить согласие
            logger.info(f"[{self.bank_code}] STEP 2: Requesting account consent...")
            consent_data = await self.request_account_consent(access_token, user_id)
            
            if not consent_data:
                logger.error(f"[{self.bank_code}] STEP 2 FAILED: No consent")
                return {
                    "success": False,
                    "bank_code": self.bank_code,
                    "error": "Failed to request account consent"
                }
            
            consent_id = consent_data.get("consent_id")
            logger.info(f"[{self.bank_code}] STEP 2 SUCCESS: Consent ID = {consent_id}")
            
            # ШАГ 3: Получить счета
            logger.info(f"[{self.bank_code}] STEP 3: Fetching user accounts...")
            accounts_data = await self.get_user_accounts(access_token, user_id, consent_id)
            
            if not accounts_data:
                logger.error(f"[{self.bank_code}] STEP 3 FAILED: No accounts data")
                return {
                    "success": False,
                    "bank_code": self.bank_code,
                    "error": "Failed to fetch accounts"
                }
            
            # Извлекаем счета в зависимости от формата ответа
            if 'data' in accounts_data and 'account' in accounts_data['data']:
                bills = accounts_data['data']['account']
            elif 'accounts' in accounts_data:
                bills = accounts_data['accounts']
            else:
                bills = []
            
            logger.info(f"[{self.bank_code}] STEP 3 SUCCESS: Fetched {len(bills)} accounts")
            logger.info(f"[{self.bank_code}] ===== FULL CYCLE COMPLETED SUCCESSFULLY =====")
            
            return {
                "success": True,
                "bank_code": self.bank_code,
                "bills": bills,
                "consent_id": consent_id,
                "auto_approved": consent_data.get("auto_approved", True),
                "raw_data": accounts_data  # Полные данные для отладки
            }
        
        except Exception as e:
            logger.error(f"[{self.bank_code}] Error in full cycle: {e}")
            return {
                "success": False,
                "bank_code": self.bank_code,
                "error": str(e)
            }


# ============ УТИЛИТАРНЫЕ ФУНКЦИИ ============

async def get_accounts_from_all_banks(user_id: str) -> Dict[str, Dict]:
    """
    Получить счета из всех трёх банков
    
    Args:
        user_id: ID пользователя
    
    Returns:
        dict: {
            "vbank": {"success": True, "bills": [...], ...},
            "abank": {"success": True, "bills": [...], ...},
            "sbank": {"success": False, "error": "..."}
        }
    """
    results = {}
    
    for bank_code in ["vbank", "abank", "sbank"]:
        logger.info(f"Processing bank: {bank_code}")
        try:
            service = OAuth2BankService(bank_code=bank_code)
            result = await service.get_bank_accounts_full_cycle(user_id)
            results[bank_code] = result
        except ValueError as e:
            # Банк не настроен в конфигурации
            logger.warning(f"Bank {bank_code} not configured: {e}")
            results[bank_code] = {
                "success": False,
                "bank_code": bank_code,
                "error": f"Bank not configured: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error processing bank {bank_code}: {e}")
            results[bank_code] = {
                "success": False,
                "bank_code": bank_code,
                "error": str(e)
            }
    
    return results


async def get_accounts_from_specific_banks(user_id: str, bank_codes: list) -> Dict[str, Dict]:
    """
    Получить счета из указанных банков
    
    Args:
        user_id: ID пользователя
        bank_codes: Список кодов банков, например ["vbank", "abank"]
    
    Returns:
        dict: {
            "vbank": {"success": True, "bills": [...]},
            "abank": {"success": True, "bills": [...]}
        }
    """
    results = {}
    
    for bank_code in bank_codes:
        logger.info(f"Processing bank: {bank_code}")
        try:
            service = OAuth2BankService(bank_code=bank_code)
            result = await service.get_bank_accounts_full_cycle(user_id)
            results[bank_code] = result
        except Exception as e:
            logger.error(f"Error processing bank {bank_code}: {e}")
            results[bank_code] = {
                "success": False,
                "bank_code": bank_code,
                "error": str(e)
            }
    
    return results
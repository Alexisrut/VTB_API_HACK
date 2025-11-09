import aiohttp
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings, BankConfig
from app.models import OAuthSession, User, BankUser

settings = get_settings()
logger = logging.getLogger(__name__)


class UniversalBankAPIService:
    """
    Универсальный сервис для работы с Open Banking API трёх банков:
    - Virtual Bank (vbank.open.bankingapi.ru)
    - Awesome Bank (abank.open.bankingapi.ru)
    - Smart Bank (sbank.open.bankingapi.ru)
    
    Все методы принимают bank_code как параметр для выбора банка
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    def _get_bank_config(self, bank_code: str) -> BankConfig:
        """Получить конфигурацию банка по коду"""
        return self.settings.get_bank_config(bank_code)
    
    # ==================== АУТЕНТИФИКАЦИЯ ====================
    
    async def get_bank_access_token(self, bank_code: str) -> Optional[str]:
        """
        Получить access token банка для доступа к данным клиентов
        
        POST https://{bank}.open.bankingapi.ru/auth/bank-token
        ?client_id={client_id}&client_secret={client_secret}
        
        Args:
            bank_code: Код банка ('vbank', 'abank', 'sbank')
        
        Returns:
            str: access_token или None при ошибке
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/auth/bank-token"
                params = {
                    "client_id": bank.client_id,
                    "client_secret": bank.client_secret
                }
                
                logger.info(f"[{bank_code}] Getting bank token from {url}")
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        access_token = data.get("access_token")
                        logger.info(f"[{bank_code}] Successfully obtained bank access token")
                        return access_token
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to get bank token: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting bank token: {e}")
            return None
    
    # ==================== СОГЛАСИЯ (CONSENTS) ====================
    
    async def request_account_consent(
        self, 
        bank_code: str,
        access_token: str, 
        user_id: str,
        permissions: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Запросить согласие на доступ к счетам пользователя
        
        POST https://{bank}.open.bankingapi.ru/account-consents/request
        
        Args:
            bank_code: Код банка
            access_token: Токен банка
            user_id: ID пользователя
            permissions: Список разрешений (по умолчанию ReadAccountsDetail, ReadBalances)
        
        Returns:
            dict: {"status": "approved", "consent_id": "...", "auto_approved": true}
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            if permissions is None:
                permissions = ["ReadAccountsDetail", "ReadBalances"]
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/account-consents/request"
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "Content-Type": "application/json"
                }
                
                body = {
                    "client_id": f"{user_id}",
                    "permissions": permissions,
                    "reason": "Агрегация счетов для HackAPI",
                    "requesting_bank": bank.requesting_bank,
                    "requesting_bank_name": bank.requesting_bank_name
                }
                
                logger.info(f"[{bank_code}] Requesting account consent for user {user_id}")
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Consent received: {data.get('consent_id')}")
                        return {
                            "status": data.get("status", "approved"),
                            "consent_id": data.get("consent_id"),
                            "auto_approved": data.get("auto_approved", True)
                        }
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to request consent: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error requesting consent: {e}")
            return None
    
    async def get_consent_details(
        self,
        bank_code: str,
        access_token: str,
        consent_id: str
    ) -> Optional[Dict]:
        """
        Получить детали согласия
        
        GET https://{bank}.open.bankingapi.ru/account-consents/{consent_id}
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/account-consents/{consent_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank
                }
                
                logger.info(f"[{bank_code}] Getting consent details: {consent_id}")
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Consent details retrieved")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to get consent: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting consent details: {e}")
            return None
    
    async def delete_consent(
        self,
        bank_code: str,
        access_token: str,
        consent_id: str
    ) -> bool:
        """
        Удалить согласие
        
        DELETE https://{bank}.open.bankingapi.ru/account-consents/{consent_id}
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/account-consents/{consent_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank
                }
                
                logger.info(f"[{bank_code}] Deleting consent: {consent_id}")
                async with session.delete(url, headers=headers) as resp:
                    if resp.status in [200, 204]:
                        logger.info(f"[{bank_code}] Consent deleted successfully")
                        return True
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to delete consent: {resp.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"[{bank_code}] Error deleting consent: {e}")
            return False
    
    # ==================== СЧЕТА (ACCOUNTS) ====================
    
    async def get_accounts(
        self,
        bank_code: str,
        access_token: str,
        user_id: str,
        consent_id: str
    ) -> Optional[Dict]:
        """
        Получить список счетов пользователя
        
        GET https://{bank}.open.bankingapi.ru/accounts?client_id={client_id}
        
        Args:
            bank_code: Код банка
            access_token: Токен банка
            user_id: ID пользователя
            consent_id: ID согласия
        
        Returns:
            dict: {"accounts": [...]}
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts"
                
                params = {
                    "client_id": f"{user_id}"
                }
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "X-Consent-Id": consent_id,
                    "Accept": "application/json"
                }
                
                logger.info(f"[{bank_code}] Fetching accounts for user {user_id}")
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Обрабатываем разные форматы ответа
                        accounts = []
                        if isinstance(data, dict):
                            # Стандартный формат: {"accounts": [...]}
                            if "accounts" in data:
                                accounts = data.get("accounts", [])
                            # Альтернативный формат: {"data": {"account": [...]}}
                            elif "data" in data and isinstance(data["data"], dict):
                                if "account" in data["data"]:
                                    accounts = data["data"]["account"] if isinstance(data["data"]["account"], list) else [data["data"]["account"]]
                                elif "accounts" in data["data"]:
                                    accounts = data["data"]["accounts"]
                            # Если accounts на верхнем уровне
                            elif "account" in data:
                                accounts = data["account"] if isinstance(data["account"], list) else [data["account"]]
                        elif isinstance(data, list):
                            # Если ответ - это список счетов напрямую
                            accounts = data
                        
                        # Фильтруем None значения и валидируем структуру
                        cleaned_accounts = []
                        for acc in accounts:
                            if acc is None:
                                continue
                            if not isinstance(acc, dict):
                                logger.warning(f"[{bank_code}] Skipping non-dict account: {type(acc)}")
                                continue
                            
                            # Извлекаем account_id из разных возможных мест
                            account_id = (
                                acc.get("account_id") or 
                                acc.get("id") or 
                                acc.get("accountId") or
                                (acc.get("account", {}) if isinstance(acc.get("account"), dict) else {}).get("identification") or
                                (acc.get("account", {}) if isinstance(acc.get("account"), dict) else {}).get("account_id")
                            )
                            
                            if not account_id:
                                logger.warning(f"[{bank_code}] Skipping account without account_id: {acc}")
                                continue
                            
                            # Удаляем None ключи и None значения из словаря
                            cleaned_acc = {}
                            for k, v in acc.items():
                                if k is not None:  # Пропускаем None ключи
                                    # Рекурсивно очищаем вложенные словари
                                    if isinstance(v, dict):
                                        cleaned_v = {nk: nv for nk, nv in v.items() if nk is not None and nv is not None}
                                        if cleaned_v:  # Только если есть валидные данные
                                            cleaned_acc[k] = cleaned_v
                                    elif isinstance(v, list):
                                        # Очищаем список от None значений
                                        cleaned_v = [item for item in v if item is not None]
                                        if cleaned_v:
                                            cleaned_acc[k] = cleaned_v
                                    elif v is not None:  # Пропускаем None значения
                                        cleaned_acc[k] = v
                            
                            # Убеждаемся, что account_id есть в cleaned_acc
                            if "account_id" not in cleaned_acc or not cleaned_acc.get("account_id"):
                                cleaned_acc["account_id"] = str(account_id)
                            
                            if cleaned_acc:  # Только если есть валидные данные
                                cleaned_accounts.append(cleaned_acc)
                        
                        logger.info(f"[{bank_code}] Successfully fetched {len(cleaned_accounts)} accounts (filtered from {len(accounts)})")
                        return {"accounts": cleaned_accounts}
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to fetch accounts: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error fetching accounts: {e}", exc_info=True)
            return None
    
    async def get_account_details(
        self,
        bank_code: str,
        access_token: str,
        account_id: str,
        consent_id: str
    ) -> Optional[Dict]:
        """
        Получить детали конкретного счета
        
        GET https://{bank}.open.bankingapi.ru/accounts/{account_id}
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts/{account_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "X-Consent-Id": consent_id
                }
                
                logger.info(f"[{bank_code}] Getting account details: {account_id}")
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Account details retrieved")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to get account details: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting account details: {e}")
            return None
    
    # ==================== БАЛАНСЫ (BALANCES) ====================
    
    async def get_account_balances(
        self,
        bank_code: str,
        access_token: str,
        account_id: str,
        consent_id: str
    ) -> Optional[Dict]:
        """
        Получить балансы счета
        
        GET https://{bank}.open.bankingapi.ru/accounts/{account_id}/balances
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts/{account_id}/balances"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "X-Consent-Id": consent_id
                }
                
                logger.info(f"[{bank_code}] Getting balances for account: {account_id}")
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Balances retrieved")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to get balances: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting balances: {e}")
            return None
    
    # ==================== ТРАНЗАКЦИИ (TRANSACTIONS) ====================
    
    async def get_account_transactions(
        self,
        bank_code: str,
        access_token: str,
        account_id: str,
        consent_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Получить транзакции по счету
        
        GET https://{bank}.open.bankingapi.ru/accounts/{account_id}/transactions
        
        Args:
            from_date: Дата начала в формате YYYY-MM-DD
            to_date: Дата конца в формате YYYY-MM-DD
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts/{account_id}/transactions"
                
                params = {}
                if from_date:
                    params["fromBookingDateTime"] = from_date
                if to_date:
                    params["toBookingDateTime"] = to_date
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "X-Consent-Id": consent_id
                }
                
                logger.info(f"[{bank_code}] Getting transactions for account: {account_id}")
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Transactions retrieved")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to get transactions: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting transactions: {e}")
            return None
    
    # ==================== ПЛАТЕЖИ (PAYMENTS) ====================
    
    async def create_payment_consent(
        self,
        bank_code: str,
        access_token: str,
        user_id: str,
        payment_data: Dict
    ) -> Optional[Dict]:
        """
        Создать согласие на платеж
        
        POST https://{bank}.open.bankingapi.ru/payment-consents
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/payment-consents"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "Content-Type": "application/json"
                }
                
                body = {
                    "client_id": f"{bank.requesting_bank}-{user_id}",
                    **payment_data
                }
                
                logger.info(f"[{bank_code}] Creating payment consent for user {user_id}")
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Payment consent created: {data.get('consentId')}")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to create payment consent: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error creating payment consent: {e}")
            return None
    
    async def initiate_payment(
        self,
        bank_code: str,
        access_token: str,
        consent_id: str,
        payment_data: Dict
    ) -> Optional[Dict]:
        """
        Инициировать платеж
        
        POST https://{bank}.open.bankingapi.ru/payments
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/payments"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                    "X-Consent-Id": consent_id,
                    "Content-Type": "application/json"
                }
                
                logger.info(f"[{bank_code}] Initiating payment with consent {consent_id}")
                async with session.post(url, json=payment_data, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Payment initiated: {data.get('paymentId')}")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to initiate payment: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error initiating payment: {e}")
            return None
    
    async def get_payment_status(
        self,
        bank_code: str,
        access_token: str,
        payment_id: str
    ) -> Optional[Dict]:
        """
        Получить статус платежа
        
        GET https://{bank}.open.bankingapi.ru/payments/{payment_id}
        """
        try:
            bank = self._get_bank_config(bank_code)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/payments/{payment_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank
                }
                
                logger.info(f"[{bank_code}] Getting payment status: {payment_id}")
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Payment status retrieved")
                        return data
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] Failed to get payment status: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting payment status: {e}")
            return None
    
    # ==================== КОМПЛЕКСНЫЕ МЕТОДЫ ====================
    
    async def get_bank_user_id(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str
    ) -> Optional[str]:
        """
        Получить bank_user_id для пользователя и банка из базы данных
        
        Args:
            db: Database session
            user_id: Internal user ID
            bank_code: Bank code (vbank, abank, sbank)
        
        Returns:
            bank_user_id или None если не найден
        """
        try:
            result = await db.execute(
                select(BankUser).where(
                    BankUser.user_id == user_id,
                    BankUser.bank_code == bank_code
                )
            )
            bank_user = result.scalars().first()
            if bank_user:
                logger.info(f"[{bank_code}] Found bank_user_id: {bank_user.bank_user_id} for user {user_id}")
                return bank_user.bank_user_id
            else:
                logger.warning(f"[{bank_code}] No bank_user_id found for user {user_id}")
                return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting bank_user_id: {e}")
            return None
    
    async def get_all_accounts_full_cycle(
        self,
        bank_code: str,
        user_id: str,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Dict:
        """
        Выполнить полный цикл получения счетов для одного банка:
        1. Получить access token банка
        2. Получить bank_user_id из базы данных
        3. Запросить согласие
        4. Получить счета
        
        Args:
            bank_code: Bank code
            user_id: Bank user ID (если не указан, будет получен из БД)
            db: Database session (опционально, нужен для получения bank_user_id)
            internal_user_id: Internal user ID (нужен для получения bank_user_id из БД)
        
        Returns:
            dict: {"success": True/False, "accounts": [...], "consent_id": "...", "error": "..."}
        """
        try:
            logger.info(f"[{bank_code}] STARTING FULL CYCLE for user {user_id}")
            
            # Получаем bank_user_id из БД - ОБЯЗАТЕЛЬНО требуется!
            bank_user_id = None
            if db and internal_user_id:
                db_bank_user_id = await self.get_bank_user_id(db, internal_user_id, bank_code)
                if db_bank_user_id:
                    bank_user_id = db_bank_user_id
                    logger.info(f"[{bank_code}] Using bank_user_id from DB: {bank_user_id}")
                else:
                    logger.error(f"[{bank_code}] No bank_user_id found in DB for user {internal_user_id}")
                    return {
                        "success": False,
                        "error": f"No bank_user_id found for {bank_code}. Please set bank_user_id in your profile first."
                    }
            else:
                # Если нет db или internal_user_id, проверяем, что user_id выглядит как полный client_id
                # (должен содержать дефис или быть в формате teamXXX-X)
                if not ("-" in str(user_id) or user_id.startswith("team")):
                    logger.error(f"[{bank_code}] Invalid user_id format: {user_id}. Expected full client_id (e.g., team261-1)")
                    return {
                        "success": False,
                        "error": f"Invalid user_id format. Please set bank_user_id in your profile for {bank_code}."
                    }
                bank_user_id = user_id
                logger.info(f"[{bank_code}] Using provided bank_user_id: {bank_user_id}")
            
            if not bank_user_id:
                return {
                    "success": False,
                    "error": f"bank_user_id is required for {bank_code}. Please set it in your profile."
                }
            
            # ШАГ 1: Получить токен банка
            logger.info(f"[{bank_code}] STEP 1: Getting bank access token...")
            access_token = await self.get_bank_access_token(bank_code)
            
            if not access_token:
                return {
                    "success": False,
                    "error": f"Failed to obtain bank access token from {bank_code}"
                }
            
            # ШАГ 2: Запросить согласие
            logger.info(f"[{bank_code}] STEP 2: Requesting account consent for bank_user_id {bank_user_id}...")
            consent_data = await self.request_account_consent(bank_code, access_token, bank_user_id)
            
            if not consent_data:
                return {
                    "success": False,
                    "error": f"Failed to request account consent from {bank_code}"
                }
            
            consent_id = consent_data.get("consent_id")
            
            # ШАГ 3: Получить счета
            logger.info(f"[{bank_code}] STEP 3: Fetching user accounts for bank_user_id {bank_user_id}...")
            accounts_data = await self.get_accounts(bank_code, access_token, bank_user_id, consent_id)
            
            if not accounts_data:
                return {
                    "success": False,
                    "error": f"Failed to fetch accounts from {bank_code}"
                }
            
            logger.info(f"[{bank_code}] FULL CYCLE COMPLETED SUCCESSFULLY")
            return {
                "success": True,
                "bank_code": bank_code,
                "accounts": accounts_data.get("accounts", []),
                "consent_id": consent_id,
                "auto_approved": consent_data.get("auto_approved", True)
            }
        
        except Exception as e:
            logger.error(f"[{bank_code}] Error in full cycle: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_accounts_from_all_banks(
        self,
        user_id: str,
        bank_codes: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Dict[str, Dict]:
        """
        Получить счета из всех банков (или выбранных)
        
        Args:
            user_id: ID пользователя (fallback если нет в БД)
            bank_codes: Список кодов банков (если None - все банки)
            db: Database session (опционально)
            internal_user_id: Internal user ID (для получения bank_user_id из БД)
        
        Returns:
            dict: {
              "vbank": {"success": True, "accounts": [...]},
              "abank": {"success": True, "accounts": [...]},
              "sbank": {"success": False, "error": "..."}
            }
        """
        if bank_codes is None:
            bank_codes = ["vbank", "abank", "sbank"]
        
        results = {}
        
        for bank_code in bank_codes:
            logger.info(f"Processing bank: {bank_code}")
            result = await self.get_all_accounts_full_cycle(
                bank_code=bank_code,
                user_id=user_id,
                db=db,
                internal_user_id=internal_user_id
            )
            results[bank_code] = result
        
        return results


# Глобальный экземпляр сервиса
universal_bank_service = UniversalBankAPIService()

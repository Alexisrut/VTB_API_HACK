import aiohttp
import secrets
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.config import get_settings, BankConfig
from app.models import OAuthSession, User, BankUser, BankConsent

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
    
    async def _get_bank_config(self, bank_code: str, db: Optional[AsyncSession] = None) -> BankConfig:
        """Получить конфигурацию банка по коду"""
        return await self.settings.get_bank_config(bank_code, db=db)
    
    async def validate_bank_exists(self, bank_code: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Проверить существование банка, пытаясь получить токен
        
        Args:
            bank_code: Код банка для проверки
            db: Database session (опционально)
        
        Returns:
            dict: {
                "exists": True/False,
                "error": "error message" или None,
                "config": BankConfig или None
            }
        """
        try:
            # Пытаемся получить конфигурацию банка
            bank_config = await self._get_bank_config(bank_code, db=db)
            
            # Проверяем наличие обязательных полей в конфигурации
            if not bank_config.client_secret or bank_config.client_secret == "your_vbank_client_secret_here" or bank_config.client_secret.startswith("your_"):
                return {
                    "exists": False,
                    "error": f"Bank {bank_code} configuration is incomplete. Missing or invalid client_secret. Please set a valid client_secret in the bank configuration.",
                    "config": bank_config
                }
            
            if not bank_config.client_id:
                return {
                    "exists": False,
                    "error": f"Bank {bank_code} configuration is incomplete. Missing client_id.",
                    "config": bank_config
                }
            
            if not bank_config.api_url:
                return {
                    "exists": False,
                    "error": f"Bank {bank_code} configuration is incomplete. Missing api_url.",
                    "config": bank_config
                }
            
            # Пытаемся получить токен для проверки доступности банка
            access_token = await self.get_bank_access_token(bank_code, db=db)
            
            if access_token:
                return {
                    "exists": True,
                    "error": None,
                    "config": bank_config
                }
            else:
                return {
                    "exists": False,
                    "error": f"Bank {bank_code} exists in configuration but is not accessible. Failed to obtain access token. Please check that client_id and client_secret are correct and the bank API is accessible.",
                    "config": bank_config
                }
        except ValueError as e:
            return {
                "exists": False,
                "error": str(e),
                "config": None
            }
        except Exception as e:
            logger.error(f"[{bank_code}] Error validating bank: {e}", exc_info=True)
            return {
                "exists": False,
                "error": f"Error validating bank: {str(e)}",
                "config": None
            }
    
    # ==================== АУТЕНТИФИКАЦИЯ ====================
    
    async def get_bank_access_token(self, bank_code: str, db: Optional[AsyncSession] = None) -> Optional[str]:
        """
        Получить access token банка для доступа к данным клиентов
        
        POST https://{bank}.open.bankingapi.ru/auth/bank-token
        ?client_id={client_id}&client_secret={client_secret}
        
        Args:
            bank_code: Код банка (любой)
            db: Database session (опционально, для получения конфигурации из БД)
        
        Returns:
            str: access_token или None при ошибке
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
            # Проверяем наличие обязательных полей
            if not bank.client_id:
                logger.error(f"[{bank_code}] Missing client_id in bank configuration")
                return None
            
            if not bank.client_secret or bank.client_secret == "your_vbank_client_secret_here" or bank.client_secret.startswith("your_"):
                logger.error(f"[{bank_code}] Missing or invalid client_secret in bank configuration. Please set a valid client_secret.")
                return None
            
            if not bank.api_url:
                logger.error(f"[{bank_code}] Missing api_url in bank configuration")
                return None
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/auth/bank-token"
                params = {
                    "client_id": "team261",
                    "client_secret": "24ADfpV1IyoAAP7d"
                }
                
                logger.info(f"[{bank_code}] Getting bank token from {url} with client_id={bank.client_id}")
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        access_token = data.get("access_token")
                        if access_token:
                            logger.info(f"[{bank_code}] Successfully obtained bank access token")
                            return access_token
                        else:
                            logger.error(f"[{bank_code}] Token response missing access_token: {data}")
                            return None
                    else:
                        # Попытаемся извлечь JSON ошибку, если есть
                        try:
                            error_json = await resp.json()
                            error_text = str(error_json)
                            logger.error(f"[{bank_code}] Failed to get bank token: HTTP {resp.status} - {error_text}")
                        except:
                            error_text = await resp.text()
                            logger.error(f"[{bank_code}] Failed to get bank token: HTTP {resp.status} - {error_text}")
                        return None
        except ValueError as e:
            logger.error(f"[{bank_code}] Bank configuration error: {e}")
            return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting bank token: {e}", exc_info=True)
            return None
    
    # ==================== СОГЛАСИЯ (CONSENTS) ====================
    
    async def get_active_consent_from_db(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str
    ) -> Optional[BankConsent]:
        """
        Получить активное согласие из базы данных
        
        Args:
            db: Database session
            user_id: Internal user ID
            bank_code: Bank code
        
        Returns:
            BankConsent если найдено активное согласие, иначе None
        """
        try:
            stmt = select(BankConsent).where(
                and_(
                    BankConsent.user_id == user_id,
                    BankConsent.bank_code == bank_code,
                    BankConsent.status == "approved"
                )
            ).order_by(BankConsent.created_at.desc())
            
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if consent:
                # Проверяем, не истекло ли согласие
                if consent.expires_at and consent.expires_at < datetime.utcnow():
                    logger.info(f"[{bank_code}] Consent {consent.consent_id} expired, marking as revoked")
                    consent.status = "revoked"
                    await db.commit()
                    return None
                logger.info(f"[{bank_code}] Found active consent {consent.consent_id} for user {user_id}")
                return consent
            
            return None
        except Exception as e:
            logger.error(f"[{bank_code}] Error getting active consent from DB: {e}")
            return None
    
    async def check_and_poll_consent_approval(
        self,
        bank_code: str,
        access_token: str,
        consent_id: str,
        max_attempts: int = 30,
        poll_interval: int = 2,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Проверять статус согласия в интервалах времени до одобрения
        
        Args:
            bank_code: Код банка
            access_token: Токен банка
            consent_id: ID согласия для проверки
            max_attempts: Максимальное количество попыток (по умолчанию 30)
            poll_interval: Интервал между проверками в секундах (по умолчанию 2)
        
        Returns:
            dict: {"status": "approved", "consent_id": "..."} или None при ошибке/таймауте
        """
        try:
            for attempt in range(1, max_attempts + 1):
                logger.info(f"[{bank_code}] Checking consent {consent_id} status (attempt {attempt}/{max_attempts})")
                
                consent_details = await self.get_consent_details(bank_code, access_token, consent_id)
                
                if not consent_details:
                    logger.warning(f"[{bank_code}] Failed to get consent details, retrying...")
                    await asyncio.sleep(poll_interval)
                    continue
                
                # Извлекаем статус из разных возможных форматов ответа
                status = None
                consent_data = None
                if isinstance(consent_details, dict):
                    if "data" in consent_details:
                        consent_data = consent_details["data"]
                        status = consent_data.get("status")
                    else:
                        consent_data = consent_details
                        status = consent_data.get("status")
                
                # ШАГ 2: Если статус "Authorized", обновляем consent_id с данными из поля "consentId"
                if status and status.lower() in ["authorized", "authorised"]:
                    # Извлекаем новый consentId из ответа
                    new_consent_id = None
                    if consent_data:
                        new_consent_id = consent_data.get("consentId") or consent_data.get("consent_id")
                    
                    # Если получили новый consentId, обновляем его в БД
                    if new_consent_id and new_consent_id != consent_id and db and internal_user_id:
                        logger.info(f"[{bank_code}] Consent authorized! Updating consent_id from {consent_id} to {new_consent_id}")
                        
                        # Обновляем consent_id в БД
                        update_stmt = select(BankConsent).where(
                            and_(
                                BankConsent.user_id == internal_user_id,
                                BankConsent.bank_code == bank_code,
                                BankConsent.consent_id == consent_id
                            )
                        )
                        result = await db.execute(update_stmt)
                        consent = result.scalar_one_or_none()
                        
                        if consent:
                            consent.consent_id = new_consent_id
                            consent.status = "approved"
                            consent.updated_at = datetime.utcnow()
                            await db.commit()
                            logger.info(f"[{bank_code}] ✅ Updated consent_id to {new_consent_id} in database")
                            consent_id = new_consent_id  # Используем новый ID для возврата
                        else:
                            logger.warning(f"[{bank_code}] Consent {consent_id} not found in DB for update, but continuing...")
                    
                    logger.info(f"[{bank_code}] Consent {consent_id} approved!")
                    return {
                        "status": "approved",
                        "consent_id": consent_id,  # Возвращаем обновленный consent_id если был обновлен
                        "auto_approved": False
                    }
                
                if status == "approved":
                    logger.info(f"[{bank_code}] Consent {consent_id} approved!")
                    return {
                        "status": "approved",
                        "consent_id": consent_id,
                        "auto_approved": False
                    }
                elif status in ["rejected", "Rejected", "revoked", "Revoked"]:
                    logger.warning(f"[{bank_code}] Consent {consent_id} was {status}")
                    return {
                        "status": status.lower(),
                        "consent_id": consent_id,
                        "auto_approved": False
                    }
                elif status in ["pending", "AwaitingAuthorisation"]:
                    logger.info(f"[{bank_code}] Consent {consent_id} still pending, waiting...")
                    await asyncio.sleep(poll_interval)
                else:
                    logger.warning(f"[{bank_code}] Unknown consent status: {status}, retrying...")
                    await asyncio.sleep(poll_interval)
            
            logger.warning(f"[{bank_code}] Consent {consent_id} approval timeout after {max_attempts} attempts")
            return {
                "status": "pending",
                "consent_id": consent_id,
                "auto_approved": False,
                "timeout": True
            }
        except Exception as e:
            logger.error(f"[{bank_code}] Error polling consent approval: {e}")
            return None
    
    async def request_account_consent(
        self, 
        bank_code: str,
        access_token: str, 
        user_id: str,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None,
        permissions: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Запросить согласие на доступ к счетам пользователя
        
        Правила:
        1. Проверяет наличие активного согласия в БД - если есть, возвращает его
        2. Создает только ОДНО согласие (удаляет старые при создании нового)
        3. Отправляет запрос на согласие в банк
        4. Проверяет статус одобрения в интервалах времени
        5. Сохраняет согласие в БД после одобрения
        
        POST https://{bank}.open.bankingapi.ru/account-consents/request
        
        Args:
            bank_code: Код банка
            access_token: Токен банка
            user_id: Bank user ID
            db: Database session (опционально, нужен для работы с БД)
            internal_user_id: Internal user ID (нужен для работы с БД)
            permissions: Список разрешений (по умолчанию ReadAccountsDetail, ReadBalances)
        
        Returns:
            dict: {"status": "approved", "consent_id": "...", "auto_approved": true}
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
            if permissions is None:
                permissions = ["ReadAccountsDetail", "ReadBalances", "ReadTransactionsDetail"]
            
            # ШАГ 1: Проверяем наличие активного согласия в БД
            if db and internal_user_id:
                existing_consent = await self.get_active_consent_from_db(db, internal_user_id, bank_code)
                if existing_consent:
                    logger.info(f"[{bank_code}] Using existing active consent {existing_consent.consent_id}")
                    return {
                        "status": "approved",
                        "consent_id": existing_consent.consent_id,
                        "auto_approved": existing_consent.auto_approved,
                        "from_db": True
                    }
            
            # ШАГ 2: Удаляем старые согласия (создаем только ОДНО)
            if db and internal_user_id:
                # Отвязываем старые согласия от счетов перед удалением
                from app.models import BankAccount
                from sqlalchemy import update
                
                update_stmt = update(BankAccount).where(
                    and_(
                        BankAccount.user_id == internal_user_id,
                        BankAccount.bank_code == bank_code
                    )
                ).values(consent_id=None)
                await db.execute(update_stmt)
                
                # Удаляем все существующие согласия для этого пользователя и банка
                delete_stmt = delete(BankConsent).where(
                    and_(
                        BankConsent.user_id == internal_user_id,
                        BankConsent.bank_code == bank_code
                    )
                )
                await db.execute(delete_stmt)
                await db.commit()
                logger.info(f"[{bank_code}] Deleted old consents for user {internal_user_id}")
            
            # ШАГ 3: Отправляем запрос на согласие в банк
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
                
                logger.info(f"[{bank_code}] Requesting account consent:")
                logger.info(f"  URL: {url}")
                logger.info(f"  Headers: {headers}")
                logger.info(f"  Body: {body}")
                logger.info(f"  User ID: {user_id}")
                
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Consent API response: {data}")
                        
                        # API возвращает: {"status": "approved", "consent_id": "consent-abc123", "auto_approved": true}
                        # Или может быть вложено в "data": {"data": {"status": "...", "consent_id": "..."}}
                        consent_status = None
                        consent_id = None
                        auto_approved = True
                        
                        # Проверяем формат ответа
                        if isinstance(data, dict) and "data" in data:
                            # Вложенный формат
                            consent_data = data["data"]
                            consent_status = consent_data.get("status", "approved")
                            # ШАГ 1: Банк может вернуть consent_id ИЛИ request_id - используем любой из них
                            consent_id = consent_data.get("consent_id") or consent_data.get("request_id")
                            auto_approved = consent_data.get("auto_approved", True)
                        else:
                            # Плоский формат (как в примере API)
                            consent_status = data.get("status", "approved")
                            # ШАГ 1: Банк может вернуть consent_id ИЛИ request_id - используем любой из них
                            consent_id = data.get("consent_id") or data.get("request_id")
                            auto_approved = data.get("auto_approved", True)
                        
                        # КРИТИЧНО: consent_id или request_id обязателен - это ID для проверки статуса
                        if not consent_id:
                            logger.error(f"[{bank_code}] ❌ No consent_id or request_id received from bank API. Response: {data}")
                            return {
                                "error": True,
                                "error_message": f"No consent_id or request_id in bank response. Response: {data}",
                                "response_data": data
                            }
                        
                        logger.info(f"[{bank_code}] Received consent_id={consent_id}, status={consent_status}, auto_approved={auto_approved}")
                        
                        # ШАГ 4: Определяем, это consent_id или request_id
                        is_request = consent_id.startswith("req-")
                        
                        # ШАГ 5: НЕМЕДЛЕННО сохраняем consent_id/request_id в БД после получения от банка
                        if db and internal_user_id:
                            expires_at = datetime.utcnow() + timedelta(days=365)
                            
                            new_consent = BankConsent(
                                user_id=internal_user_id,
                                bank_code=bank_code,
                                consent_id=consent_id,  # Сохраняем как есть (может быть request_id)
                                status=consent_status,  # Сохраняем текущий статус (pending/approved)
                                auto_approved=auto_approved,
                                expires_at=expires_at
                            )
                            db.add(new_consent)
                            await db.commit()
                            await db.refresh(new_consent)
                            logger.info(f"[{bank_code}] ✅ Saved {'request_id' if is_request else 'consent_id'}={consent_id} to database with status={consent_status}")
                        
                        # ШАГ 6: Если это request_id (req-...), отправляем запрос на /account-consents/{request_id}
                        if is_request:
                            logger.info(f"[{bank_code}] Received request_id={consent_id}, checking status via GET /account-consents/{consent_id}...")
                            request_details = await self.get_consent_details(
                                bank_code=bank_code,
                                access_token=access_token,
                                consent_id=consent_id  # Используем request_id для запроса
                            )
                            
                            if request_details:
                                # Извлекаем данные из ответа
                                request_data = None
                                if isinstance(request_details, dict) and "data" in request_details:
                                    request_data = request_details["data"]
                                else:
                                    request_data = request_details
                                
                                if request_data:
                                    # Проверяем, есть ли consentId в ответе
                                    final_consent_id = request_data.get("consentId") or request_data.get("consent_id")
                                    final_status = request_data.get("status", consent_status)
                                    
                                    # Если получили consentId, обновляем в БД
                                    if final_consent_id and final_consent_id != consent_id:
                                        logger.info(f"[{bank_code}] ✅ Received consentId={final_consent_id} from request_id={consent_id}, updating in DB...")
                                        
                                        if db and internal_user_id:
                                            # Обновляем запись в БД: заменяем request_id на consent_id
                                            update_stmt = select(BankConsent).where(
                                                and_(
                                                    BankConsent.user_id == internal_user_id,
                                                    BankConsent.bank_code == bank_code,
                                                    BankConsent.consent_id == consent_id  # Ищем по request_id
                                                )
                                            )
                                            result = await db.execute(update_stmt)
                                            consent = result.scalar_one_or_none()
                                            if consent:
                                                consent.consent_id = final_consent_id
                                                consent.status = final_status
                                                consent.updated_at = datetime.utcnow()
                                                await db.commit()
                                                logger.info(f"[{bank_code}] ✅ Updated consent_id from {consent_id} to {final_consent_id} in database")
                                                consent_id = final_consent_id  # Используем новый consent_id
                                                consent_status = final_status
                                            else:
                                                logger.error(f"[{bank_code}] ❌ Request {consent_id} not found in DB for update!")
                                    else:
                                        # Нет consentId, возможно еще pending
                                        consent_status = final_status
                                        logger.info(f"[{bank_code}] Request {consent_id} status: {final_status}, no consentId yet")
                            else:
                                logger.warning(f"[{bank_code}] Failed to get request details for {consent_id}")
                        
                        return {
                            "status": consent_status,
                            "consent_id": consent_id,  # Может быть request_id или consent_id
                            "auto_approved": auto_approved,
                            "is_request": is_request
                        }
                    else:
                        error_text = await resp.text()
                        logger.error(f"[{bank_code}] ❌ Failed to request consent: HTTP {resp.status} - {error_text}")
                        # Return error details instead of None for better debugging
                        return {
                            "error": True,
                            "status_code": resp.status,
                            "error_message": error_text,
                            "url": url
                        }
        except Exception as e:
            logger.error(f"[{bank_code}] ❌ Error requesting consent: {e}", exc_info=True)
            # Return error details instead of None
            return {
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__
            }
    
    async def validate_consent_for_use(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str,
        consent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверить согласие перед использованием
        
        Args:
            db: Database session
            user_id: Internal user ID
            bank_code: Bank code
            consent_id: Optional consent_id для проверки конкретного согласия
        
        Returns:
            dict: {
                "valid": True/False,
                "consent": BankConsent или None,
                "error": "error message" или None
            }
        """
        try:
            if consent_id:
                # Проверяем конкретное согласие
                stmt = select(BankConsent).where(
                    and_(
                        BankConsent.consent_id == consent_id,
                        BankConsent.user_id == user_id,
                        BankConsent.bank_code == bank_code
                    )
                )
            else:
                # Ищем активное согласие
                stmt = select(BankConsent).where(
                    and_(
                        BankConsent.user_id == user_id,
                        BankConsent.bank_code == bank_code
                    )
                ).order_by(BankConsent.created_at.desc())
            
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if not consent:
                return {
                    "valid": False,
                    "consent": None,
                    "error": "Consent not found. Please create a consent first."
                }
            
            if consent.status == "revoked":
                return {
                    "valid": False,
                    "consent": consent,
                    "error": "Consent was deleted/revoked. Please create a new consent."
                }
            
            if consent.status != "approved":
                return {
                    "valid": False,
                    "consent": consent,
                    "error": f"Consent is not approved. Current status: {consent.status}. Please wait for approval or create a new consent."
                }
            
            # Проверяем срок действия
            if consent.expires_at and consent.expires_at < datetime.utcnow():
                consent.status = "revoked"
                await db.commit()
                return {
                    "valid": False,
                    "consent": consent,
                    "error": "Consent has expired. Please create a new consent."
                }
            
            return {
                "valid": True,
                "consent": consent,
                "error": None
            }
        except Exception as e:
            logger.error(f"[{bank_code}] Error validating consent: {e}")
            return {
                "valid": False,
                "consent": None,
                "error": f"Error validating consent: {str(e)}"
            }
    
    async def get_consent_details(
        self,
        bank_code: str,
        access_token: str,
        consent_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict]:
        """
        Получить детали согласия
        
        GET https://{bank}.open.bankingapi.ru/account-consents/{consent_id}
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/account-consents/{consent_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank
                }
                
                logger.info(f"[{bank_code}] Getting consent details via GET {url}")
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Consent details retrieved for consent_id={consent_id}: {data}")
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
        consent_id: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Удалить согласие
        
        DELETE https://{bank}.open.bankingapi.ru/account-consents/{consent_id}
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
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
        consent_id: str,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Получить список счетов пользователя
        
        GET https://{bank}.open.bankingapi.ru/accounts?client_id={client_id}
        
        Args:
            bank_code: Код банка
            access_token: Токен банка
            user_id: ID пользователя
            consent_id: ID согласия
            db: Database session (опционально, для проверки согласия)
            internal_user_id: Internal user ID (для проверки согласия)
        
        Returns:
            dict: {"accounts": [...]} или {"error": "..."} если согласие не одобрено
        """
        try:
            # Проверяем согласие перед использованием
            if db and internal_user_id:
                validation = await self.validate_consent_for_use(db, internal_user_id, bank_code, consent_id)
                if not validation["valid"]:
                    logger.error(f"[{bank_code}] Cannot use consent: {validation['error']}")
                    return {
                        "error": validation["error"],
                        "consent_status": validation["consent"].status if validation["consent"] else "not_found"
                    }
            bank = await self._get_bank_config(bank_code, db=db)
            
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
        consent_id: str,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Получить детали конкретного счета
        
        GET https://{bank}.open.bankingapi.ru/accounts/{account_id}
        """
        try:
            # Проверяем согласие перед использованием
            if db and internal_user_id:
                validation = await self.validate_consent_for_use(db, internal_user_id, bank_code, consent_id)
                if not validation["valid"]:
                    logger.error(f"[{bank_code}] Cannot use consent: {validation['error']}")
                    return {
                        "error": validation["error"],
                        "consent_status": validation["consent"].status if validation["consent"] else "not_found"
                    }
            bank = await self._get_bank_config(bank_code, db=db)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts/{account_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                }
                
                # Добавляем X-Consent-Id только если он не None
                if consent_id:
                    headers["X-Consent-Id"] = consent_id
                
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
        consent_id: str,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Получить балансы счета
        
        GET https://{bank}.open.bankingapi.ru/accounts/{account_id}/balances
        """
        try:
            # Проверяем согласие перед использованием
            if db and internal_user_id:
                validation = await self.validate_consent_for_use(db, internal_user_id, bank_code, consent_id)
                if not validation["valid"]:
                    logger.error(f"[{bank_code}] Cannot use consent: {validation['error']}")
                    return {
                        "error": validation["error"],
                        "consent_status": validation["consent"].status if validation["consent"] else "not_found"
                    }
            bank = await self._get_bank_config(bank_code, db=db)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts/{account_id}/balances"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                }
                
                # Добавляем X-Consent-Id только если он не None
                if consent_id:
                    headers["X-Consent-Id"] = consent_id
                
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
        from_booking_date_time: Optional[str] = None,
        to_booking_date_time: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        internal_user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Получить транзакции по счету
        
        GET https://{bank}.open.bankingapi.ru/accounts/{account_id}/transactions
        
        Согласно OpenAPI спецификации:
        - from_booking_date_time: Дата начала в формате ISO 8601 (например: "2025-01-01T00:00:00Z")
        - to_booking_date_time: Дата конца в формате ISO 8601 (например: "2025-12-31T23:59:59Z")
        - page: Номер страницы (по умолчанию: 1)
        - limit: Количество транзакций на странице (по умолчанию: 50, макс: 500)
        
        Args:
            from_booking_date_time: Дата начала в формате ISO 8601 или YYYY-MM-DD (будет преобразована)
            to_booking_date_time: Дата конца в формате ISO 8601 или YYYY-MM-DD (будет преобразована)
            page: Номер страницы
            limit: Количество транзакций на странице (макс: 500)
            db: Database session (опционально, для проверки согласия)
            internal_user_id: Internal user ID (для проверки согласия)
        """
        try:
            # Проверяем согласие перед использованием
            if db and internal_user_id:
                validation = await self.validate_consent_for_use(db, internal_user_id, bank_code, consent_id)
                if not validation["valid"]:
                    logger.error(f"[{bank_code}] Cannot use consent: {validation['error']}")
                    return {
                        "error": validation["error"],
                        "consent_status": validation["consent"].status if validation["consent"] else "not_found"
                    }
            bank = await self._get_bank_config(bank_code, db=db)
            
            async with aiohttp.ClientSession() as session:
                url = f"{bank.api_url}/accounts/{account_id}/transactions"
                
                params = {}
                
                # Преобразуем даты в формат ISO 8601 если нужно
                if from_booking_date_time:
                    # Если дата в формате YYYY-MM-DD, добавляем время
                    if len(from_booking_date_time) == 10:
                        from_booking_date_time = f"{from_booking_date_time}T00:00:00Z"
                    params["from_booking_date_time"] = from_booking_date_time
                
                if to_booking_date_time:
                    # Если дата в формате YYYY-MM-DD, добавляем время
                    if len(to_booking_date_time) == 10:
                        to_booking_date_time = f"{to_booking_date_time}T23:59:59Z"
                    params["to_booking_date_time"] = to_booking_date_time
                
                if page is not None:
                    params["page"] = page
                
                if limit is not None:
                    # Ограничиваем максимум 500 согласно OpenAPI
                    limit = min(limit, 500)
                    params["limit"] = limit
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "X-Requesting-Bank": bank.requesting_bank,
                }
                
                # Добавляем X-Consent-Id только если он не None
                if consent_id:
                    headers["X-Consent-Id"] = consent_id
                
                logger.info(f"[{bank_code}] Getting transactions for account: {account_id}, params: {params}")
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"[{bank_code}] Transactions retrieved")
                        
                        # Обрабатываем разные форматы ответа (как с балансами)
                        # Может быть: {"transactions": [...]} или {"data": {"transaction": [...]}}
                        if isinstance(data, dict):
                            # Стандартный формат: {"transactions": [...]}
                            if "transactions" in data:
                                return data
                            # Альтернативный формат: {"data": {"transaction": [...]}}
                            elif "data" in data and isinstance(data["data"], dict):
                                if "transaction" in data["data"]:
                                    transactions = data["data"]["transaction"]
                                    if not isinstance(transactions, list):
                                        transactions = [transactions]
                                    return {"transactions": transactions}
                                elif "transactions" in data["data"]:
                                    return {"transactions": data["data"]["transactions"]}
                            # Если transactions на верхнем уровне
                            elif "transaction" in data:
                                transactions = data["transaction"]
                                if not isinstance(transactions, list):
                                    transactions = [transactions]
                                return {"transactions": transactions}
                        
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
        payment_data: Dict,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict]:
        """
        Создать согласие на платеж
        
        POST https://{bank}.open.bankingapi.ru/payment-consents
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
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
        payment_data: Dict,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict]:
        """
        Инициировать платеж
        
        POST https://{bank}.open.bankingapi.ru/payments
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
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
        payment_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict]:
        """
        Получить статус платежа
        
        GET https://{bank}.open.bankingapi.ru/payments/{payment_id}
        """
        try:
            bank = await self._get_bank_config(bank_code, db=db)
            
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
            access_token = await self.get_bank_access_token(bank_code, db=db)
            
            if not access_token:
                return {
                    "success": False,
                    "error": f"Failed to obtain bank access token from {bank_code}"
                }
            
            # ШАГ 2: Запросить согласие
            logger.info(f"[{bank_code}] STEP 2: Requesting account consent for bank_user_id {bank_user_id}...")
            consent_data = await self.request_account_consent(
                bank_code=bank_code,
                access_token=access_token,
                user_id=bank_user_id,
                db=db,
                internal_user_id=internal_user_id
            )
            
            if not consent_data:
                return {
                    "success": False,
                    "error": f"Failed to request account consent from {bank_code}"
                }
            
            consent_id = consent_data.get("consent_id")
            consent_status = consent_data.get("status", "approved")
            
            # Проверяем, что согласие одобрено
            if consent_status != "approved":
                return {
                    "success": False,
                    "error": f"Consent is not approved. Status: {consent_status}. Please wait for approval or create a new consent.",
                    "consent_id": consent_id,
                    "consent_status": consent_status
                }
            
            # ШАГ 3: Получить счета
            logger.info(f"[{bank_code}] STEP 3: Fetching user accounts for bank_user_id {bank_user_id}...")
            accounts_data = await self.get_accounts(
                bank_code=bank_code,
                access_token=access_token,
                user_id=bank_user_id,
                consent_id=consent_id,
                db=db,
                internal_user_id=internal_user_id
            )
            
            if not accounts_data:
                return {
                    "success": False,
                    "error": f"Failed to fetch accounts from {bank_code}"
                }
            
            # Проверяем, есть ли ошибка в ответе (например, согласие не одобрено)
            if isinstance(accounts_data, dict) and "error" in accounts_data:
                return {
                    "success": False,
                    "error": accounts_data.get("error"),
                    "consent_status": accounts_data.get("consent_status")
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
            # Получаем список банков из конфигурации
            if db:
                try:
                    all_banks = await self.settings.get_all_banks(db=db)
                    bank_codes = list(all_banks.keys())
                except Exception as e:
                    logger.warning(f"Failed to get banks from config, using defaults: {e}")
                    bank_codes = ["vbank", "abank", "sbank"]
            else:
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

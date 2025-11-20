from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import asyncio

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.universal_bank_service import universal_bank_service
from app.services.data_aggregation_service import data_aggregation_service
from app.bank_schemas import (
    GetBankAccountsResponse,
    BankAccountSchema,
    BankTransactionSchema,
    BankBalanceSchema,
    GetBankTransactionsResponse,
    GetBankBalanceHistoryResponse
)

router = APIRouter(prefix="/api/v1/banks", tags=["Open Banking API"])
logger = logging.getLogger(__name__)

# ==================== HELPER FUNCTIONS ====================

async def validate_bank_code(bank_code: str, db: AsyncSession) -> None:
    """
    Валидировать существование банка
    
    Raises:
        HTTPException: Если банк не найден или недоступен
    """
    validation = await universal_bank_service.validate_bank_exists(
        bank_code=bank_code,
        db=db
    )
    
    if not validation["exists"]:
        error_msg = validation.get("error", f"Bank {bank_code} not found or not accessible")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BANK_NOT_FOUND",
                "message": error_msg,
                "bank_code": bank_code,
                "hint": f"Please add the bank configuration first. Bank {bank_code} is not configured or not accessible."
            }
        )

# ==================== ПОЛУЧЕНИЕ СЧЕТОВ ====================

@router.get("/accounts", response_model=GetBankAccountsResponse)
async def get_user_accounts(
    bank_code: str = Query(..., description="Код банка (например: vbank, abank, sbank или любой другой)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список счетов пользователя из конкретного банка
    
    **Параметры:**
    - **bank_code**: Код банка (любой поддерживаемый банк)
    
    **Возвращает:**
    - Список счетов с балансами
    
    **Примечание:**
    - Использует bank_user_id из профиля пользователя, если он установлен
    - Если bank_user_id не установлен, вернет ошибку с инструкцией
    - Если банк не найден, вернет ошибку с инструкцией по добавлению банка
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        logger.info(f"User {user_id} requesting accounts from {bank_code}")
        
        # Используем data_aggregation_service для получения и сохранения счетов в БД
        result = await data_aggregation_service.fetch_and_save_accounts(
            bank_code=bank_code,
            user_id=user_id,
            db=db
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Failed to fetch accounts")
            # Проверяем, не связана ли ошибка с отсутствием bank_user_id
            if "No bank_user_id" in error_msg or "bank_user_id" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{error_msg}. Please set bank_user_id in your profile first."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Фильтруем и валидируем счета перед сериализацией
        valid_accounts = []
        accounts_list = result.get("accounts", [])
        
        for acc in accounts_list:
            # Пропускаем счета без account_id или с None в качестве ключей
            if not isinstance(acc, dict):
                logger.warning(f"[{bank_code}] Skipping invalid account format: {type(acc)}")
                continue
            
            # Проверяем наличие account_id из разных возможных мест
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
            
            # Удаляем None ключи и None значения из словаря (рекурсивно)
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
            
            # Убеждаемся, что account_id есть в cleaned_acc и это строка
            if "account_id" not in cleaned_acc or not cleaned_acc.get("account_id"):
                cleaned_acc["account_id"] = str(account_id)
            
            try:
                valid_accounts.append(BankAccountSchema(**cleaned_acc))
            except Exception as e:
                logger.warning(f"[{bank_code}] Skipping account due to validation error: {e}, account: {cleaned_acc}")
                continue
        
        return GetBankAccountsResponse(
            success=True,
            accounts=valid_accounts,
            consent_id=result.get("consent_id"),
            auto_approved=result.get("auto_approved")
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/accounts/all")
async def get_accounts_from_all_banks(
    user_id: int = Depends(get_current_user),
    banks: Optional[List[str]] = Query(None, description="Список кодов банков (например: vbank,abank,sbank)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить счета из всех банков или выбранных
    
    **Параметры:**
    - **banks**: Список кодов банков (если не указано - все банки пользователя)
    
    **Возвращает:**
    - Счета из каждого банка с флагами успешности
    
    **Примечание:**
    - Использует bank_user_id из профиля пользователя для каждого банка
    - Если банк не найден, вернет ошибку для этого банка
    """
    try:
        logger.info(f"User {user_id} requesting accounts from multiple banks")
        
        # Если banks не указан, получаем список банков пользователя
        if not banks:
            from app.models import BankUser
            from sqlalchemy import select
            result = await db.execute(
                select(BankUser.bank_code).where(BankUser.user_id == user_id).distinct()
            )
            banks = [row[0] for row in result.all()]
            
            if not banks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No banks configured for user. Please add bank_user_id for at least one bank first."
                )
        
        # Валидируем все банки перед обработкой
        for bank_code in banks:
            try:
                await validate_bank_code(bank_code, db)
            except HTTPException as e:
                logger.warning(f"Bank {bank_code} validation failed: {e.detail}")
                # Продолжаем, но этот банк вернет ошибку в результатах
        
        results = await universal_bank_service.get_accounts_from_all_banks(
            user_id=str(user_id),  # Fallback если нет в БД
            bank_codes=banks,
            db=db,
            internal_user_id=user_id
        )
        
        # Форматируем ответ
        response = {
            "success": True,
            "banks": {}
        }
        
        total_accounts = 0
        for bank_code, bank_result in results.items():
            if bank_result.get("success"):
                accounts = bank_result.get("accounts", [])
                total_accounts += len(accounts)
                response["banks"][bank_code] = {
                    "success": True,
                    "accounts": accounts,
                    "consent_id": bank_result.get("consent_id"),
                    "count": len(accounts)
                }
            else:
                error_msg = bank_result.get("error", "Unknown error")
                response["banks"][bank_code] = {
                    "success": False,
                    "error": error_msg,
                    "count": 0
                }
        
        response["total_accounts"] = total_accounts
        return response
    
    except Exception as e:
        logger.error(f"Error getting accounts from all banks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/accounts/{account_id}")
async def get_account_details(
    account_id: str,
    bank_code: str = Query(..., description="Код банка"),
    consent_id: str = Query(..., description="ID согласия"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о конкретном счете
    
    **Параметры:**
    - **account_id**: ID счета
    - **bank_code**: Код банка
    - **consent_id**: ID согласия
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        # Получаем токен банка
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        # Получаем детали счета
        account_data = await universal_bank_service.get_account_details(
            bank_code=bank_code,
            access_token=access_token,
            account_id=account_id,
            consent_id=consent_id,
            db=db,
            internal_user_id=user_id
        )
        
        if not account_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        return {
            "success": True,
            "account": account_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== БАЛАНСЫ ====================

@router.get("/accounts/{account_id}/balances")
async def get_account_balances(
    account_id: str,
    bank_code: str = Query(..., description="Код банка"),
    consent_id: Optional[str] = Query(None, description="ID согласия (если не указано, будет получен из БД)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить балансы счета
    
    **Параметры:**
    - **account_id**: ID счета
    - **bank_code**: Код банка
    - **consent_id**: ID согласия (опционально, если не указано - будет получен из БД)
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        # Если consent_id не указан, получаем его из БД
        if not consent_id:
            from app.models import BankConsent
            from sqlalchemy import select, and_
            
            # Ищем любое активное согласие (не отозванное)
            stmt = select(BankConsent).where(
                and_(
                    BankConsent.user_id == user_id,
                    BankConsent.bank_code == bank_code,
                    # Разрешаем approved, authorized, valid и т.д., главное не revoked/rejected/pending
                    BankConsent.status.in_(["approved", "authorized", "authorised", "given", "valid", "active"])
                )
            ).order_by(BankConsent.created_at.desc())
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if not consent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No active consent found for {bank_code}. Please check consent status in profile."
                )
            consent_id = consent.consent_id
            logger.info(f"Using consent_id from DB: {consent_id} for bank {bank_code}")
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        balances_data = await universal_bank_service.get_account_balances(
            bank_code=bank_code,
            access_token=access_token,
            account_id=account_id,
            consent_id=consent_id,
            db=db,
            internal_user_id=user_id
        )
        
        if not balances_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Balances not found"
            )
        
        return {
            "success": True,
            "balances": balances_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ТРАНЗАКЦИИ ====================

@router.get("/accounts/{account_id}/transactions", response_model=GetBankTransactionsResponse)
async def get_account_transactions(
    account_id: str,
    bank_code: str = Query(..., description="Код банка"),
    consent_id: Optional[str] = Query(None, description="ID согласия (если не указано, будет получен из БД)"),
    from_booking_date_time: Optional[str] = Query(None, alias="from_date", description="Дата начала в формате ISO 8601 (например: 2025-01-01T00:00:00Z) или YYYY-MM-DD"),
    to_booking_date_time: Optional[str] = Query(None, alias="to_date", description="Дата конца в формате ISO 8601 (например: 2025-12-31T23:59:59Z) или YYYY-MM-DD"),
    page: Optional[int] = Query(None, ge=1, description="Номер страницы (по умолчанию: 1)"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Количество транзакций на странице (по умолчанию: 50, макс: 500)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить транзакции по счету с использованием кэширования (Read-Through Caching).
    
    Сначала проверяет локальную базу данных. Если данные устарели (старше 5 минут),
    синхронизирует их с банком и затем возвращает из БД.
    
    **Параметры:**
    - **account_id**: ID счета
    - **bank_code**: Код банка
    - **from_date**: Дата начала
    - **to_date**: Дата конца
    - **page**: Номер страницы
    - **limit**: Количество на странице
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        # Валидация параметров пагинации
        if page is None or page < 1:
            page = 1
        if limit is None or limit < 1:
            limit = 50
        if limit > 500:
            limit = 500
            
        # Обработка дат
        from_date = None
        if from_booking_date_time:
            if len(from_booking_date_time) == 10:
                from_booking_date_time += "T00:00:00Z"
            try:
                from_date = datetime.fromisoformat(from_booking_date_time.replace("Z", "+00:00"))
            except ValueError:
                pass # Игнорируем ошибку, если дата некорректна, будет None
                
        to_date = None
        if to_booking_date_time:
            if len(to_booking_date_time) == 10:
                to_booking_date_time += "T23:59:59Z"
            try:
                to_date = datetime.fromisoformat(to_booking_date_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Получаем данные через сервис с кэшированием
        result = await data_aggregation_service.get_transactions_read_through(
            db=db,
            user_id=user_id,
            account_id=account_id,
            bank_code=bank_code,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
            ttl_seconds=300 # 5 минут кэш
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if "not found" in str(result.get("error")).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get transactions")
            )
            
        transactions = result.get("transactions", [])
        formatted_transactions = []
        
        for tx in transactions:
            try:
                formatted_transactions.append(BankTransactionSchema(**tx))
            except Exception as e:
                logger.warning(f"Skipping invalid transaction schema: {e}")
                continue
                
        return GetBankTransactionsResponse(
            success=True,
            account_id=account_id,
            transactions=formatted_transactions,
            total_count=result.get("total_count", len(formatted_transactions))
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== СОГЛАСИЯ ====================

async def _poll_consent_and_fetch_accounts(
    bank_code: str,
    consent_id: str,
    user_id: int,
    bank_user_id: str,
    db: AsyncSession
):
    """
    Фоновая задача для проверки статуса согласия и получения счетов после одобрения
    """
    from app.models import BankConsent
    from sqlalchemy import select, and_
    from datetime import datetime
    import asyncio
    
    try:
        max_attempts = 30  # 30 попыток
        poll_interval = 2  # 2 секунды между попытками
        
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(poll_interval)
            
            # Получаем доступный токен
            access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
            if not access_token:
                logger.warning(f"[{bank_code}] No access token for consent polling, attempt {attempt}")
                continue
            
            # Проверяем статус согласия
            consent_details = await universal_bank_service.get_consent_details(
                bank_code=bank_code,
                access_token=access_token,
                consent_id=consent_id,
                db=db
            )
            
            if not consent_details:
                logger.warning(f"[{bank_code}] Failed to get consent details, attempt {attempt}")
                continue
            
            # Извлекаем статус
            status = None
            if isinstance(consent_details, dict):
                if "data" in consent_details:
                    status = consent_details["data"].get("status")
                else:
                    status = consent_details.get("status")
            
            logger.info(f"[{bank_code}] Consent {consent_id} status check {attempt}/{max_attempts}: {status}")
            
            if status in ["approved", "Authorised"]:
                # Обновляем статус в БД
                stmt = select(BankConsent).where(
                    and_(
                        BankConsent.user_id == user_id,
                        BankConsent.bank_code == bank_code,
                        BankConsent.consent_id == consent_id
                    )
                )
                result = await db.execute(stmt)
                consent = result.scalar_one_or_none()
                
                if consent:
                    consent.status = "approved"
                    consent.updated_at = datetime.utcnow()
                    await db.commit()
                    logger.info(f"[{bank_code}] Consent {consent_id} approved and updated in DB")
                
                # Получаем счета
                try:
                    accounts_data = await universal_bank_service.get_accounts(
                        bank_code=bank_code,
                        access_token=access_token,
                        user_id=bank_user_id,
                        consent_id=consent_id,
                        db=db,
                        internal_user_id=user_id
                    )
                    
                    if accounts_data and "accounts" in accounts_data:
                        accounts_count = len(accounts_data["accounts"])
                        logger.info(f"[{bank_code}] Successfully fetched {accounts_count} accounts after consent approval")
                    else:
                        logger.warning(f"[{bank_code}] No accounts returned after consent approval")
                except Exception as e:
                    logger.error(f"[{bank_code}] Error fetching accounts after consent approval: {e}")
                
                return
            
            elif status in ["rejected", "Rejected", "revoked", "Revoked"]:
                # Обновляем статус в БД
                stmt = select(BankConsent).where(
                    and_(
                        BankConsent.user_id == user_id,
                        BankConsent.bank_code == bank_code,
                        BankConsent.consent_id == consent_id
                    )
                )
                result = await db.execute(stmt)
                consent = result.scalar_one_or_none()
                
                if consent:
                    consent.status = status.lower()
                    consent.updated_at = datetime.utcnow()
                    await db.commit()
                    logger.info(f"[{bank_code}] Consent {consent_id} {status} and updated in DB")
                
                return
            
            # Если все еще pending, продолжаем проверку
        
        logger.warning(f"[{bank_code}] Consent {consent_id} polling timeout after {max_attempts} attempts")
    
    except Exception as e:
        logger.error(f"[{bank_code}] Error in consent polling task: {e}", exc_info=True)


@router.post("/account-consents")
async def create_account_consent(
    bank_code: str = Query(..., description="Код банка"),
    permissions: Optional[List[str]] = Query(None, description="Список разрешений (по умолчанию: ReadAccountsDetail, ReadBalances, ReadTransactionsDetail)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать согласие на доступ к счетам пользователя
    
    Создает согласие и сохраняет его в БД для последующего использования.
    Для каждого банка создается отдельное согласие.
    
    **Параметры:**
    - **bank_code**: Код банка (любой поддерживаемый банк)
    - **permissions**: Список разрешений (опционально)
    
    **Разрешения:**
    - ReadAccountsDetail - доступ к деталям счетов
    - ReadBalances - доступ к балансам
    - ReadTransactionsDetail - доступ к транзакциям (обязательно для получения транзакций)
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        from app.models import BankConsent, BankUser
        from sqlalchemy import select, and_
        from datetime import datetime, timedelta
        
        # Получаем bank_user_id для пользователя
        stmt = select(BankUser).where(
            and_(
                BankUser.user_id == user_id,
                BankUser.bank_code == bank_code
            )
        )
        result = await db.execute(stmt)
        bank_user = result.scalar_one_or_none()
        
        if not bank_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bank user ID not found for {bank_code}. Please set it in profile first."
            )
        
        bank_user_id = bank_user.bank_user_id
        
        # Используем дефолтные разрешения, если не указаны
        if permissions is None:
            permissions = ["ReadAccountsDetail", "ReadBalances", "ReadTransactionsDetail"]
        
        # Убеждаемся, что ReadTransactionsDetail всегда включен для работы с транзакциями
        if "ReadTransactionsDetail" not in permissions:
            permissions.append("ReadTransactionsDetail")
        
        # Получаем токен банка
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            logger.error(f"[{bank_code}] Failed to obtain access token for consent creation")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to obtain bank access token for {bank_code}. Please check bank configuration."
            )
        
        logger.info(f"[{bank_code}] Access token obtained successfully for consent creation")
        
        # Создаем согласие через API банка
        consent_data = await universal_bank_service.request_account_consent(
            bank_code=bank_code,
            access_token=access_token,
            user_id=bank_user_id,
            db=db,
            internal_user_id=user_id,
            permissions=permissions
        )
        
        if not consent_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create consent: No response from bank API"
            )
        
        # Check if consent_data contains an error
        if isinstance(consent_data, dict) and consent_data.get("error"):
            error_msg = consent_data.get("error_message", "Unknown error")
            status_code = consent_data.get("status_code", status.HTTP_400_BAD_REQUEST)
            logger.error(f"[{bank_code}] Consent creation error: {error_msg}")
            raise HTTPException(
                status_code=status_code,
                detail=f"Failed to create consent: {error_msg}"
            )
        
        consent_id = consent_data.get("consent_id")
        consent_status = consent_data.get("status", "approved")
        auto_approved = consent_data.get("auto_approved", True)
        
        # Проверяем, что consent_id не None
        if not consent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Согласие создано, но consent_id отсутствует. Статус: {consent_status}."
            )
        
        # Вычисляем дату истечения для ответа (по умолчанию 365 дней)
        expires_at = datetime.utcnow() + timedelta(days=365)
        
        # Примечание: consent уже сохранен в БД внутри request_account_consent
        # ШАГ 1: consent_id или request_id получен от банка
        # ШАГ 2: consent/request сохранен в БД с текущим статусом (pending/approved)
        # ШАГ 3: если это request_id (req-...), отправлен запрос на /account-consents/{request_id}
        # ШАГ 4: если получен consentId из request, обновлен в БД
        # ШАГ 5: пользователь может проверить статус вручную через кнопку "Обновить"
        
        # Формируем сообщение в зависимости от статуса
        if consent_status == "pending" or consent_data.get("is_request"):
            message = f"Согласие создано и ожидает одобрения в банке {bank_code}. Используйте кнопку 'Обновить' для проверки статуса."
        else:
            # Если согласие сразу одобрено, получаем счета
            try:
                accounts_data = await universal_bank_service.get_accounts(
                    bank_code=bank_code,
                    access_token=access_token,
                    user_id=bank_user_id,
                    consent_id=consent_id,
                    db=db,
                    internal_user_id=user_id
                )
                if accounts_data and "accounts" in accounts_data:
                    accounts_count = len(accounts_data["accounts"])
                    message = f"Consent approved. Fetched {accounts_count} account(s)."
                else:
                    message = "Consent approved successfully."
            except Exception as e:
                logger.error(f"Error fetching accounts after consent approval: {e}")
                message = "Consent approved. Error fetching accounts - will retry later."
        
        return {
            "success": True,
            "consent_id": consent_id,
            "status": consent_status,
            "auto_approved": auto_approved,
            "permissions": permissions,
            "expires_at": expires_at.isoformat(),
            "message": message
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/consents")
async def get_user_consents(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех согласий пользователя
    
    Возвращает все согласия пользователя для всех банков.
    Также проверяет актуальный статус согласий у банка (для обнаружения удаленных согласий).
    """
    try:
        from app.models import BankConsent, BankUser
        from sqlalchemy import select, and_
        
        stmt = select(BankConsent).where(
            BankConsent.user_id == user_id
        ).order_by(BankConsent.created_at.desc())
        
        result = await db.execute(stmt)
        consents = result.scalars().all()
        
        # Проверяем актуальный статус каждого согласия у банка
        updated_consents = []
        for consent in consents:
            try:
                # Получаем токен банка
                access_token = await universal_bank_service.get_bank_access_token(consent.bank_code, db=db)
                if access_token:
                    # Проверяем статус согласия у банка
                    consent_details = await universal_bank_service.get_consent_details(
                        bank_code=consent.bank_code,
                        access_token=access_token,
                        consent_id=consent.consent_id,
                        db=db
                    )
                    
                    if consent_details:
                        # Извлекаем статус из ответа банка
                        bank_status = None
                        if isinstance(consent_details, dict):
                            if "data" in consent_details:
                                bank_status = consent_details["data"].get("status")
                            else:
                                bank_status = consent_details.get("status")
                        
                        # Если согласие удалено/отозвано на стороне банка, обновляем в БД
                        if bank_status in ["revoked", "Revoked", "rejected", "Rejected"]:
                            consent.status = bank_status.lower()
                            consent.updated_at = datetime.utcnow()
                            await db.commit()
                            logger.info(f"[{consent.bank_code}] Consent {consent.consent_id} status updated to {bank_status}")
                        elif bank_status in ["approved", "Authorised"] and consent.status != "approved":
                            # Согласие одобрено на стороне банка, обновляем в БД
                            consent.status = "approved"
                            consent.updated_at = datetime.utcnow()
                            await db.commit()
                            logger.info(f"[{consent.bank_code}] Consent {consent.consent_id} approved and updated in DB")
                    else:
                        # Не удалось получить детали - возможно, согласие удалено
                        logger.warning(f"[{consent.bank_code}] Could not get consent details for {consent.consent_id}, possibly revoked")
                        if consent.status == "approved":
                            consent.status = "revoked"
                            consent.updated_at = datetime.utcnow()
                            await db.commit()
                
            except Exception as e:
                logger.error(f"Error checking consent {consent.consent_id} status: {e}")
            
            updated_consents.append({
                "consent_id": consent.consent_id,
                "bank_code": consent.bank_code,
                "status": consent.status,
                "auto_approved": consent.auto_approved,
                "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                "created_at": consent.created_at.isoformat(),
                "updated_at": consent.updated_at.isoformat()
            })
        
        return {
            "success": True,
            "consents": updated_consents
        }
    
    except Exception as e:
        logger.error(f"Error getting user consents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/consents/{consent_id}")
async def get_consent_details(
    consent_id: str,
    bank_code: str = Query(..., description="Код банка"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детали согласия и проверить актуальный статус у банка
    
    **Параметры:**
    - **consent_id**: ID согласия
    - **bank_code**: Код банка
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        from app.models import BankConsent
        from sqlalchemy import select, and_
        from datetime import datetime
        
        # Проверяем, что согласие принадлежит пользователю
        stmt = select(BankConsent).where(
            and_(
                BankConsent.consent_id == consent_id,
                BankConsent.user_id == user_id,
                BankConsent.bank_code == bank_code
            )
        )
        result = await db.execute(stmt)
        db_consent = result.scalar_one_or_none()
        
        if not db_consent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consent not found"
            )
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        consent_data = await universal_bank_service.get_consent_details(
            bank_code=bank_code,
            access_token=access_token,
            consent_id=consent_id,
            db=db
        )
        
        if not consent_data:
            # Согласие не найдено у банка - возможно, удалено
            db_consent.status = "revoked"
            db_consent.updated_at = datetime.utcnow()
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consent not found or revoked at bank"
            )
        
        # Извлекаем данные из ответа
        response_data = None
        if isinstance(consent_data, dict) and "data" in consent_data:
            response_data = consent_data["data"]
        else:
            response_data = consent_data
        
        # Извлекаем актуальный статус и consentId из ответа банка
        bank_status = response_data.get("status") if response_data else None
        consent_id_from_response = response_data.get("consentId") or response_data.get("consent_id") if response_data else None
        
        # Если это request_id (req-...) и пришел consentId, обновляем в БД
        if consent_id.startswith("req-") and consent_id_from_response and consent_id_from_response != consent_id:
            logger.info(f"[{bank_code}] Request {consent_id} approved, updating to consent_id={consent_id_from_response}")
            db_consent.consent_id = consent_id_from_response
            consent_id = consent_id_from_response  # Используем новый ID для дальнейшей обработки
        
        # Обновляем статус в БД, если изменился
        if bank_status:
            bank_status_lower = bank_status.lower()
            
            # Маппинг статусов: authorized/given/valid -> approved
            if bank_status_lower in ["authorized", "authorised", "given", "valid", "active"]:
                bank_status_lower = "approved"
            
            if bank_status_lower != db_consent.status:
                old_status = db_consent.status
                db_consent.status = bank_status_lower
                db_consent.updated_at = datetime.utcnow()
                await db.commit()
                logger.info(f"[{bank_code}] Consent {consent_id} status updated from {old_status} to {bank_status_lower}")
            else:
                # Обновляем updated_at даже если статус не изменился
                db_consent.updated_at = datetime.utcnow()
                await db.commit()
        
        return {
            "success": True,
            "consent": consent_data,
            "db_status": db_consent.status,
            "consent_id": db_consent.consent_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/consents/{consent_id}")
async def delete_consent(
    consent_id: str,
    bank_code: str = Query(..., description="Код банка"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить согласие
    
    **Параметры:**
    - **consent_id**: ID согласия
    - **bank_code**: Код банка
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        success = await universal_bank_service.delete_consent(
            bank_code=bank_code,
            access_token=access_token,
            consent_id=consent_id,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete consent"
            )
        
        return {
            "success": True,
            "message": "Consent deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ПЛАТЕЖИ ====================

@router.post("/payments/consents")
async def create_payment_consent(
    bank_code: str = Query(..., description="Код банка"),
    payment_data: dict = None,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать согласие на платеж
    
    **Параметры:**
    - **bank_code**: Код банка
    - **payment_data**: Данные платежа
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        consent_data = await universal_bank_service.create_payment_consent(
            bank_code=bank_code,
            access_token=access_token,
            user_id=str(user_id),
            payment_data=payment_data,
            db=db
        )
        
        if not consent_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create payment consent"
            )
        
        return {
            "success": True,
            "consent": consent_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/payments")
async def initiate_payment(
    bank_code: str = Query(..., description="Код банка"),
    consent_id: str = Query(..., description="ID согласия на платеж"),
    payment_data: dict = None,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Инициировать платеж
    
    **Параметры:**
    - **bank_code**: Код банка
    - **consent_id**: ID согласия на платеж
    - **payment_data**: Данные платежа
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        payment_result = await universal_bank_service.initiate_payment(
            bank_code=bank_code,
            access_token=access_token,
            consent_id=consent_id,
            payment_data=payment_data,
            db=db
        )
        
        if not payment_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to initiate payment"
            )
        
        return {
            "success": True,
            "payment": payment_result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/payments/{payment_id}")
async def get_payment_status(
    payment_id: str,
    bank_code: str = Query(..., description="Код банка"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статус платежа
    
    **Параметры:**
    - **payment_id**: ID платежа
    - **bank_code**: Код банка
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        payment_status = await universal_bank_service.get_payment_status(
            bank_code=bank_code,
            access_token=access_token,
            payment_id=payment_id,
            db=db
        )
        
        if not payment_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        return {
            "success": True,
            "payment": payment_status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== УТИЛИТЫ ====================

@router.get("/banks/list")
async def list_available_banks(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список доступных банков (из БД и env)
    """
    try:
        from app.config import get_settings
        settings = get_settings()
        
        # Получаем все банки из конфигурации (БД + env)
        all_banks = await settings.get_all_banks(db=db)
        
        banks_list = []
        for bank_code, bank_config in all_banks.items():
            banks_list.append({
                "code": bank_code,
                "name": bank_config.requesting_bank_name or f"{bank_code.title()} Bank",
                "url": bank_config.api_url
            })
        
        return {
            "banks": banks_list
        }
    except Exception as e:
        logger.error(f"Error getting banks list: {e}")
        # Fallback на стандартные банки
        return {
            "banks": [
                {
                    "code": "vbank",
                    "name": "Virtual Bank",
                    "url": "https://vbank.open.bankingapi.ru"
                },
                {
                    "code": "abank",
                    "name": "Awesome Bank",
                    "url": "https://abank.open.bankingapi.ru"
                },
                {
                    "code": "sbank",
                    "name": "Smart Bank",
                    "url": "https://sbank.open.bankingapi.ru"
                }
            ]
        }


@router.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

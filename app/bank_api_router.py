from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import asyncio

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.universal_bank_service import universal_bank_service
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
        
        result = await universal_bank_service.get_all_accounts_full_cycle(
            bank_code=bank_code,
            user_id=str(user_id),  # Fallback если нет в БД
            db=db,
            internal_user_id=user_id
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
            stmt = select(BankConsent).where(
                and_(
                    BankConsent.user_id == user_id,
                    BankConsent.bank_code == bank_code,
                    BankConsent.status == "approved"
                )
            ).order_by(BankConsent.created_at.desc())
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if not consent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No active consent found for {bank_code}. Please sync accounts first."
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
    Получить транзакции по счету
    
    Согласно OpenAPI спецификации и логике bank-in-a-box:
    - Поддерживает пагинацию (page, limit)
    - Фильтрация по датам (from_booking_date_time, to_booking_date_time)
    - Требует согласие с разрешением ReadTransactionsDetail
    
    **Параметры:**
    - **account_id**: ID счета
    - **bank_code**: Код банка
    - **consent_id**: ID согласия (опционально, если не указано - будет получен из БД)
    - **from_booking_date_time** (или **from_date**): Дата начала в формате ISO 8601 или YYYY-MM-DD
    - **to_booking_date_time** (или **to_date**): Дата конца в формате ISO 8601 или YYYY-MM-DD
    - **page**: Номер страницы (по умолчанию: 1)
    - **limit**: Количество транзакций на странице (по умолчанию: 50, макс: 500)
    
    **Требования:**
    - Согласие должно быть активным (status="approved")
    - Согласие должно содержать разрешение ReadTransactionsDetail
    - Согласие не должно быть истекшим
    """
    try:
        # Валидируем существование банка
        await validate_bank_code(bank_code, db)
        
        from app.models import BankConsent
        from sqlalchemy import select, and_
        from datetime import datetime
        
        # Валидация параметров пагинации (согласно логике bank-in-a-box)
        if page is None or page < 1:
            page = 1
        if limit is None or limit < 1:
            limit = 50
        if limit > 500:
            limit = 500
        
        # Если consent_id не указан, получаем его из БД
        if not consent_id:
            stmt = select(BankConsent).where(
                and_(
                    BankConsent.user_id == user_id,
                    BankConsent.bank_code == bank_code,
                    BankConsent.status == "approved"
                )
            ).order_by(BankConsent.created_at.desc())
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if not consent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "CONSENT_REQUIRED",
                        "message": f"Требуется согласие клиента для доступа к транзакциям. Получите согласие через POST /account-consents с permissions=['ReadTransactionsDetail']"
                    }
                )
            
            # Проверяем, что согласие не истекло
            if consent.expires_at and consent.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "CONSENT_EXPIRED",
                        "message": "Согласие истекло. Получите новое согласие через POST /account-consents с permissions=['ReadTransactionsDetail']"
                    }
                )
            
            consent_id = consent.consent_id
            logger.info(f"Using consent_id from DB: {consent_id} for bank {bank_code}")
        else:
            # Если consent_id указан, проверяем его существование и валидность
            stmt = select(BankConsent).where(
                and_(
                    BankConsent.consent_id == consent_id,
                    BankConsent.user_id == user_id,
                    BankConsent.bank_code == bank_code,
                    BankConsent.status == "approved"
                )
            )
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if not consent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "CONSENT_NOT_FOUND",
                        "message": f"Согласие {consent_id} не найдено или не активно"
                    }
                )
            
            # Проверяем, что согласие не истекло
            if consent.expires_at and consent.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "CONSENT_EXPIRED",
                        "message": "Согласие истекло. Получите новое согласие через POST /account-consents с permissions=['ReadTransactionsDetail']"
                    }
                )
        
        # Примечание: Проверка разрешения ReadTransactionsDetail происходит на стороне банка
        # при запросе транзакций. Если согласие не содержит это разрешение, банк вернет ошибку.
        # В bank-in-a-box это проверяется через ConsentService.check_consent с permissions=["ReadTransactionsDetail"]
        # В нашем случае, мы полагаемся на проверку со стороны банка, так как permissions
        # не хранятся в нашей БД, но должны быть включены при создании согласия.
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code, db=db)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        transactions_data = await universal_bank_service.get_account_transactions(
            bank_code=bank_code,
            access_token=access_token,
            account_id=account_id,
            consent_id=consent_id,
            from_booking_date_time=from_booking_date_time,
            to_booking_date_time=to_booking_date_time,
            page=page,
            limit=limit,
            db=db,
            internal_user_id=user_id
        )
        
        if not transactions_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transactions not found"
            )
        
        transactions = transactions_data.get("transactions", [])
        
        # Преобразуем транзакции в формат схемы
        formatted_transactions = []
        for tx in transactions:
            # Преобразуем accountId -> account_id
            tx_account_id = tx.get("accountId") or tx.get("account_id") or account_id
            
            # Преобразуем amount из объекта в число
            tx_amount = None
            tx_currency = None
            if "amount" in tx:
                if isinstance(tx["amount"], dict):
                    # Формат: {"amount": {"amount": "1570.56", "currency": "RUB"}}
                    tx_amount = float(tx["amount"].get("amount", 0)) if tx["amount"].get("amount") else None
                    tx_currency = tx["amount"].get("currency")
                elif isinstance(tx["amount"], str):
                    # Формат: "1570.56"
                    tx_amount = float(tx["amount"]) if tx["amount"] else None
                else:
                    tx_amount = float(tx["amount"]) if tx["amount"] else None
            
            # Если currency не в amount, берем из верхнего уровня
            if not tx_currency:
                tx_currency = tx.get("currency")
            
            # Преобразуем даты
            booking_date = None
            value_date = None
            if tx.get("bookingDateTime"):
                try:
                    booking_date = datetime.fromisoformat(tx["bookingDateTime"].replace("Z", "+00:00"))
                except:
                    pass
            if tx.get("valueDateTime"):
                try:
                    value_date = datetime.fromisoformat(tx["valueDateTime"].replace("Z", "+00:00"))
                except:
                    pass
            
            # Формируем транзакцию в формате схемы
            formatted_tx = {
                "transaction_id": tx.get("transactionId") or tx.get("transaction_id"),
                "account_id": tx_account_id,
                "amount": tx_amount,
                "currency": tx_currency,
                "transaction_type": tx.get("creditDebitIndicator") or tx.get("transaction_type"),
                "booking_date": booking_date,
                "value_date": value_date,
                "remittance_information": (
                    tx.get("transactionInformation") or 
                    tx.get("remittanceInformation", {}).get("unstructured") if isinstance(tx.get("remittanceInformation"), dict) else tx.get("remittanceInformation") or
                    tx.get("remittance_information")
                ),
                "creditor_name": tx.get("creditorName") or tx.get("creditor_name"),
                "creditor_account": tx.get("creditorAccount", {}).get("identification") if isinstance(tx.get("creditorAccount"), dict) else tx.get("creditor_account"),
                "debtor_name": tx.get("debtorName") or tx.get("debtor_name"),
                "debtor_account": tx.get("debtorAccount", {}).get("identification") if isinstance(tx.get("debtorAccount"), dict) else tx.get("debtor_account"),
            }
            
            formatted_transactions.append(BankTransactionSchema(**formatted_tx))
        
        return GetBankTransactionsResponse(
            success=True,
            account_id=account_id,
            transactions=formatted_transactions,
            total_count=len(formatted_transactions)
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
        # ШАГ 1: consent_id получен от банка
        # ШАГ 2: consent сохранен в БД с текущим статусом (pending/approved) 
        # ШАГ 3: если pending, request_account_consent уже делает polling и обновит статус
        # ШАГ 4: после одобрения, consent обновлен в БД и готов к использованию
        
        # Если согласие pending, оно уже сохранено и проверяется внутри request_account_consent
        # Но запускаем дополнительную фоновую задачу на случай, если основной polling завершится с ошибкой
        if consent_status == "pending":
            # Запускаем асинхронную задачу для проверки статуса согласия (как backup)
            asyncio.create_task(
                _poll_consent_and_fetch_accounts(
                    bank_code=bank_code,
                    consent_id=consent_id,
                    user_id=user_id,
                    bank_user_id=bank_user_id,
                    db=db
                )
            )
            message = f"Согласие создано и ожидает одобрения в банке {bank_code}. Проверяю статус..."
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
        
        # Извлекаем актуальный статус из ответа банка
        bank_status = None
        if isinstance(consent_data, dict):
            if "data" in consent_data:
                bank_status = consent_data["data"].get("status")
            else:
                bank_status = consent_data.get("status")
        
        # Обновляем статус в БД, если изменился
        if bank_status and bank_status.lower() != db_consent.status:
            old_status = db_consent.status
            db_consent.status = bank_status.lower()
            db_consent.updated_at = datetime.utcnow()
            await db.commit()
            logger.info(f"[{bank_code}] Consent {consent_id} status updated from {old_status} to {bank_status.lower()}")
        
        return {
            "success": True,
            "consent": consent_data,
            "db_status": db_consent.status
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

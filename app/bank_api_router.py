from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import logging

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

# ==================== ПОЛУЧЕНИЕ СЧЕТОВ ====================

@router.get("/accounts", response_model=GetBankAccountsResponse)
async def get_user_accounts(
    bank_code: str = Query(..., description="Код банка: vbank, abank, sbank"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список счетов пользователя из конкретного банка
    
    **Параметры:**
    - **bank_code**: Код банка ('vbank', 'abank', 'sbank')
    
    **Возвращает:**
    - Список счетов с балансами
    
    **Примечание:**
    - Использует bank_user_id из профиля пользователя, если он установлен
    - Если bank_user_id не установлен, вернет ошибку с инструкцией
    """
    try:
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
    banks: Optional[List[str]] = Query(None, description="Список банков (vbank,abank,sbank)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить счета из всех банков или выбранных
    
    **Параметры:**
    - **banks**: Список кодов банков (если не указано - все банки)
    
    **Возвращает:**
    - Счета из каждого банка с флагами успешности
    
    **Примечание:**
    - Использует bank_user_id из профиля пользователя для каждого банка
    """
    try:
        logger.info(f"User {user_id} requesting accounts from multiple banks")
        
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
        # Получаем токен банка
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
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
            consent_id=consent_id
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
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        balances_data = await universal_bank_service.get_account_balances(
            bank_code=bank_code,
            access_token=access_token,
            account_id=account_id,
            consent_id=consent_id
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
        
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
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
            limit=limit
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
    - **bank_code**: Код банка (vbank, abank, sbank)
    - **permissions**: Список разрешений (опционально)
    
    **Разрешения:**
    - ReadAccountsDetail - доступ к деталям счетов
    - ReadBalances - доступ к балансам
    - ReadTransactionsDetail - доступ к транзакциям (обязательно для получения транзакций)
    """
    try:
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
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        # Создаем согласие через API банка
        consent_data = await universal_bank_service.request_account_consent(
            bank_code=bank_code,
            access_token=access_token,
            user_id=bank_user_id,
            permissions=permissions
        )
        
        if not consent_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create consent"
            )
        
        consent_id = consent_data.get("consent_id")
        consent_status = consent_data.get("status", "approved")
        auto_approved = consent_data.get("auto_approved", True)
        request_id = consent_data.get("request_id")  # Для pending согласий может быть request_id
        
        # Если согласие в статусе pending и нет consent_id, используем request_id
        if consent_status == "pending" and not consent_id and request_id:
            consent_id = request_id
            logger.info(f"[{bank_code}] Using request_id as consent_id for pending consent: {request_id}")
        
        # Проверяем, что consent_id не None перед сохранением
        if not consent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "CONSENT_ID_MISSING",
                    "message": f"Согласие создано, но consent_id отсутствует. Статус: {consent_status}. Возможно, требуется ручное одобрение в банке {bank_code}."
                }
            )
        
        # Вычисляем дату истечения (по умолчанию 365 дней)
        expires_at = datetime.utcnow() + timedelta(days=365)
        
        # Проверяем, есть ли уже согласие для этого пользователя и банка
        # Ищем как approved, так и pending согласия
        existing_stmt = select(BankConsent).where(
            and_(
                BankConsent.user_id == user_id,
                BankConsent.bank_code == bank_code
            )
        ).order_by(BankConsent.created_at.desc())
        existing_result = await db.execute(existing_stmt)
        existing_consent = existing_result.scalar_one_or_none()
        
        if existing_consent:
            # Обновляем существующее согласие
            existing_consent.consent_id = consent_id
            existing_consent.status = consent_status
            existing_consent.auto_approved = auto_approved
            existing_consent.expires_at = expires_at
            existing_consent.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing_consent)
            logger.info(f"Updated consent {consent_id} for user {user_id} and bank {bank_code}, status: {consent_status}")
        else:
            # Создаем новое согласие
            new_consent = BankConsent(
                user_id=user_id,
                bank_code=bank_code,
                consent_id=consent_id,
                status=consent_status,
                auto_approved=auto_approved,
                expires_at=expires_at
            )
            db.add(new_consent)
            await db.commit()
            await db.refresh(new_consent)
            logger.info(f"Created new consent {consent_id} for user {user_id} and bank {bank_code}, status: {consent_status}")
        
        # Формируем сообщение в зависимости от статуса
        if consent_status == "pending":
            message = f"Согласие создано и ожидает одобрения в банке {bank_code}. После одобрения оно будет автоматически активировано."
        else:
            message = "Consent created and saved successfully"
        
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
    """
    try:
        from app.models import BankConsent
        from sqlalchemy import select, and_
        
        stmt = select(BankConsent).where(
            BankConsent.user_id == user_id
        ).order_by(BankConsent.created_at.desc())
        
        result = await db.execute(stmt)
        consents = result.scalars().all()
        
        return {
            "success": True,
            "consents": [
                {
                    "consent_id": consent.consent_id,
                    "bank_code": consent.bank_code,
                    "status": consent.status,
                    "auto_approved": consent.auto_approved,
                    "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                    "created_at": consent.created_at.isoformat(),
                    "updated_at": consent.updated_at.isoformat()
                }
                for consent in consents
            ]
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
    Получить детали согласия
    
    **Параметры:**
    - **consent_id**: ID согласия
    - **bank_code**: Код банка
    """
    try:
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        consent_data = await universal_bank_service.get_consent_details(
            bank_code=bank_code,
            access_token=access_token,
            consent_id=consent_id
        )
        
        if not consent_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consent not found"
            )
        
        return {
            "success": True,
            "consent": consent_data
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
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        success = await universal_bank_service.delete_consent(
            bank_code=bank_code,
            access_token=access_token,
            consent_id=consent_id
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
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        consent_data = await universal_bank_service.create_payment_consent(
            bank_code=bank_code,
            access_token=access_token,
            user_id=str(user_id),
            payment_data=payment_data
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
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        payment_result = await universal_bank_service.initiate_payment(
            bank_code=bank_code,
            access_token=access_token,
            consent_id=consent_id,
            payment_data=payment_data
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
        access_token = await universal_bank_service.get_bank_access_token(bank_code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to obtain bank token"
            )
        
        payment_status = await universal_bank_service.get_payment_status(
            bank_code=bank_code,
            access_token=access_token,
            payment_id=payment_id
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
async def list_available_banks():
    """
    Получить список доступных банков
    """
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

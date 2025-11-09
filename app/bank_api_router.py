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
    consent_id: str = Query(..., description="ID согласия"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить балансы счета
    
    **Параметры:**
    - **account_id**: ID счета
    - **bank_code**: Код банка
    - **consent_id**: ID согласия
    """
    try:
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
    from_date: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="Дата конца YYYY-MM-DD"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить транзакции по счету
    
    **Параметры:**
    - **account_id**: ID счета
    - **bank_code**: Код банка
    - **consent_id**: ID согласия (опционально, если не указано - будет получен из БД)
    - **from_date**: Дата начала (опционально)
    - **to_date**: Дата конца (опционально)
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
        
        transactions_data = await universal_bank_service.get_account_transactions(
            bank_code=bank_code,
            access_token=access_token,
            account_id=account_id,
            consent_id=consent_id,
            from_date=from_date,
            to_date=to_date
        )
        
        if not transactions_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transactions not found"
            )
        
        transactions = transactions_data.get("transactions", [])
        
        return GetBankTransactionsResponse(
            success=True,
            account_id=account_id,
            transactions=[BankTransactionSchema(**tx) for tx in transactions],
            total_count=len(transactions)
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

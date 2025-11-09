"""
Роутер для синхронизации данных из банков
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.data_aggregation_service import data_aggregation_service

router = APIRouter(prefix="/api/v1/sync", tags=["Data Synchronization"])


@router.post("/accounts")
async def sync_accounts(
    bank_code: Optional[str] = Query(None, description="Код банка (если не указано - все банки)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать счета из банков
    
    **Параметры:**
    - **bank_code**: Код банка (vbank, abank, sbank) или все банки
    """
    try:
        result = await data_aggregation_service.sync_user_accounts(
            db=db,
            user_id=user_id,
            bank_code=bank_code
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to sync accounts")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/transactions")
async def sync_transactions(
    account_id: Optional[int] = Query(None, description="ID счета (если не указано - все счета)"),
    days_back: int = Query(90, ge=1, le=365, description="За сколько дней назад получать транзакции"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать транзакции из банков
    
    **Параметры:**
    - **account_id**: ID счета (если не указано - все активные счета)
    - **days_back**: За сколько дней назад получать транзакции (1-365, по умолчанию 90)
    """
    try:
        if account_id:
            # Синхронизируем конкретный счет
            from app.models import BankAccount, BankConsent
            
            account = await db.get(BankAccount, account_id)
            if not account or account.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Account not found"
                )
            
            # Получаем согласие
            from sqlalchemy import select, and_
            stmt = select(BankConsent).where(
                and_(
                    BankConsent.user_id == user_id,
                    BankConsent.bank_code == account.bank_code,
                    BankConsent.status == "approved"
                )
            ).order_by(BankConsent.created_at.desc())
            
            result = await db.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if not consent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active consent for this bank"
                )
            
            sync_result = await data_aggregation_service.sync_account_transactions(
                db=db,
                user_id=user_id,
                account_id=account_id,
                bank_code=account.bank_code,
                consent_id=consent.consent_id,
                days_back=days_back
            )
            
            if not sync_result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=sync_result.get("error", "Failed to sync transactions")
                )
            
            return sync_result
        else:
            # Синхронизируем все счета
            result = await data_aggregation_service.sync_all_accounts_transactions(
                db=db,
                user_id=user_id,
                days_back=days_back
            )
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "Failed to sync transactions")
                )
            
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/all")
async def sync_all(
    days_back: int = Query(90, ge=1, le=365, description="За сколько дней назад получать транзакции"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Полная синхронизация: счета + транзакции
    
    **Параметры:**
    - **days_back**: За сколько дней назад получать транзакции (1-365, по умолчанию 90)
    """
    try:
        # Синхронизируем счета
        accounts_result = await data_aggregation_service.sync_user_accounts(
            db=db,
            user_id=user_id
        )
        
        # Синхронизируем транзакции
        transactions_result = await data_aggregation_service.sync_all_accounts_transactions(
            db=db,
            user_id=user_id,
            days_back=days_back
        )
        
        return {
            "success": True,
            "accounts": accounts_result,
            "transactions": transactions_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


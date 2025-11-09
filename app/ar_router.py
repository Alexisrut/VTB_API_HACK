"""
Роутер для управления дебиторской задолженностью (Accounts Receivable)
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.ar_management_service import ar_management_service

router = APIRouter(prefix="/api/v1/ar", tags=["Accounts Receivable"])


class CreateInvoiceRequest(BaseModel):
    counterparty_id: int
    invoice_number: str
    invoice_date: str  # ISO format
    due_date: str  # ISO format
    amount: float
    currency: str = "RUB"
    description: Optional[str] = None
    auto_reminder_enabled: bool = True
    reminder_days_before: int = 3


class MarkPaidRequest(BaseModel):
    paid_amount: Optional[float] = None
    payment_transaction_id: Optional[int] = None


@router.post("/invoices")
async def create_invoice(
    request: CreateInvoiceRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать счет к получению
    
    **Параметры:**
    - **counterparty_id**: ID контрагента
    - **invoice_number**: Номер счета
    - **invoice_date**: Дата счета (ISO format)
    - **due_date**: Срок оплаты (ISO format)
    - **amount**: Сумма счета
    - **currency**: Валюта (по умолчанию RUB)
    - **description**: Описание
    - **auto_reminder_enabled**: Включить автоматические напоминания
    - **reminder_days_before**: За сколько дней напоминать
    """
    try:
        invoice_date = datetime.fromisoformat(request.invoice_date.replace("Z", "+00:00"))
        due_date = datetime.fromisoformat(request.due_date.replace("Z", "+00:00"))
        
        result = await ar_management_service.create_invoice(
            db=db,
            user_id=user_id,
            counterparty_id=request.counterparty_id,
            invoice_number=request.invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            amount=Decimal(str(request.amount)),
            currency=request.currency,
            description=request.description,
            auto_reminder_enabled=request.auto_reminder_enabled,
            reminder_days_before=request.reminder_days_before
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create invoice")
            )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/invoices")
async def get_invoices(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    counterparty_id: Optional[int] = Query(None, description="Фильтр по контрагенту"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список счетов к получению
    
    **Параметры:**
    - **status**: Фильтр по статусу (pending, partial, paid, overdue, cancelled)
    - **counterparty_id**: Фильтр по контрагенту
    """
    try:
        result = await ar_management_service.get_invoices(
            db=db,
            user_id=user_id,
            status=status,
            counterparty_id=counterparty_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to get invoices")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: int,
    request: MarkPaidRequest = Body(...),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отметить счет как оплаченный
    
    **Параметры:**
    - **invoice_id**: ID счета
    - **paid_amount**: Сумма оплаты (если не указано - полная оплата)
    - **payment_transaction_id**: ID транзакции оплаты
    """
    try:
        paid_amount = Decimal(str(request.paid_amount)) if request.paid_amount else None
        
        result = await ar_management_service.mark_as_paid(
            db=db,
            user_id=user_id,
            invoice_id=invoice_id,
            paid_amount=paid_amount,
            payment_transaction_id=request.payment_transaction_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to mark invoice as paid")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/overdue")
async def get_overdue_invoices(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить просроченные счета
    
    **Возвращает:**
    - Список просроченных счетов с количеством дней просрочки
    """
    try:
        result = await ar_management_service.get_overdue_invoices(
            db=db,
            user_id=user_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to get overdue invoices")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/summary")
async def get_ar_summary(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить сводку по дебиторской задолженности
    
    **Возвращает:**
    - Общая сумма ДЗ, просроченная ДЗ, количество счетов
    """
    try:
        result = await ar_management_service.get_ar_summary(
            db=db,
            user_id=user_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to get AR summary")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/auto-match")
async def auto_match_payments(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Автоматически сопоставить входящие платежи со счетами
    
    **Возвращает:**
    - Количество сопоставленных счетов
    """
    try:
        result = await ar_management_service.auto_match_payments(
            db=db,
            user_id=user_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to auto-match payments")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


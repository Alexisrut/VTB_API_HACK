"""
Роутер для управления контрагентами
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.counterparty_service import counterparty_service

router = APIRouter(prefix="/api/v1/counterparties", tags=["Counterparties"])


class CreateCounterpartyRequest(BaseModel):
    name: str
    type: str  # customer, supplier, other
    inn: Optional[str] = None
    kpp: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bic: Optional[str] = None
    correspondent_account: Optional[str] = None
    notes: Optional[str] = None


class UpdateCounterpartyRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bic: Optional[str] = None
    correspondent_account: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("")
async def create_counterparty(
    request: CreateCounterpartyRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать контрагента
    
    **Параметры:**
    - **name**: Название контрагента
    - **type**: Тип (customer, supplier, other)
    - **inn**: ИНН
    - **kpp**: КПП
    - **email**: Email
    - **phone**: Телефон
    - **account_number**: Номер счета
    - **bank_name**: Название банка
    - **bic**: БИК
    - **correspondent_account**: Корреспондентский счет
    - **notes**: Заметки
    """
    try:
        result = await counterparty_service.create_counterparty(
            db=db,
            user_id=user_id,
            name=request.name,
            type=request.type,
            inn=request.inn,
            kpp=request.kpp,
            email=request.email,
            phone=request.phone,
            account_number=request.account_number,
            bank_name=request.bank_name,
            bic=request.bic,
            correspondent_account=request.correspondent_account,
            notes=request.notes
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create counterparty")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("")
async def list_counterparties(
    type: Optional[str] = Query(None, description="Фильтр по типу (customer, supplier, other)"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список контрагентов
    
    **Параметры:**
    - **type**: Фильтр по типу
    - **search**: Поиск по названию
    """
    try:
        result = await counterparty_service.list_counterparties(
            db=db,
            user_id=user_id,
            type=type,
            search=search
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to list counterparties")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{counterparty_id}")
async def get_counterparty(
    counterparty_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить контрагента с деталями и статистикой
    
    **Параметры:**
    - **counterparty_id**: ID контрагента
    """
    try:
        result = await counterparty_service.get_counterparty(
            db=db,
            user_id=user_id,
            counterparty_id=counterparty_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "Counterparty not found")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{counterparty_id}")
async def update_counterparty(
    counterparty_id: int,
    request: UpdateCounterpartyRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить данные контрагента
    
    **Параметры:**
    - **counterparty_id**: ID контрагента
    - Все остальные поля опциональны
    """
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        result = await counterparty_service.update_counterparty(
            db=db,
            user_id=user_id,
            counterparty_id=counterparty_id,
            **update_data
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to update counterparty")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/from-transaction/{transaction_id}")
async def create_counterparty_from_transaction(
    transaction_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Автоматически создать контрагента из транзакции
    
    **Параметры:**
    - **transaction_id**: ID транзакции
    """
    try:
        result = await counterparty_service.auto_create_from_transaction(
            db=db,
            user_id=user_id,
            transaction_id=transaction_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create counterparty from transaction")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


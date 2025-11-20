from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Dict, Optional
from app.models import User, BankUser, BankConfigModel
from app.schemas import UserResponse
from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.universal_bank_service import universal_bank_service
import logging

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о текущем пользователе"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user information: {str(e)}"
        )

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    update_data: dict,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление профиля пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    for key, value in update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)

@router.post("/logout")
async def logout(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Выход из системы"""
    return {"message": "Successfully logged out"}


# ==================== BANK USER ID MANAGEMENT ====================

class BankUserCreate(BaseModel):
    bank_code: str
    bank_user_id: str
    
    @field_validator("bank_code", "bank_user_id")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class BankUserResponse(BaseModel):
    id: int
    user_id: int
    bank_code: str
    bank_user_id: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/me/bank-users")
async def get_user_bank_users(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить все bank_user_id для текущего пользователя"""
    try:
        result = await db.execute(
            select(BankUser).where(BankUser.user_id == user_id)
        )
        bank_users = result.scalars().all()
        
        # Формируем словарь {bank_code: bank_user_id}
        bank_users_dict: Dict[str, str] = {}
        for bank_user in bank_users:
            bank_users_dict[bank_user.bank_code] = bank_user.bank_user_id
        
        return {"bank_users": bank_users_dict}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving bank users: {str(e)}"
        )


@router.post("/me/bank-users", response_model=BankUserResponse)
async def save_bank_user(
    bank_user_data: BankUserCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Сохранить или обновить bank_user_id для банка
    
    Валидирует существование банка перед добавлением.
    Если банк не найден, возвращает ошибку.
    """
    try:
        # Валидируем существование банка
        validation = await universal_bank_service.validate_bank_exists(
            bank_code=bank_user_data.bank_code,
            db=db
        )
        
        if not validation["exists"]:
            error_msg = validation.get("error", f"Bank {bank_user_data.bank_code} not found or not accessible")
            logger.error(f"Bank validation failed for {bank_user_data.bank_code}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg  # Return string instead of dict for better error handling
            )
        
        # Если банк валиден, убеждаемся что конфигурация банка есть в БД
        bank_config = validation.get("config")
        if bank_config:
            # Проверяем, есть ли конфигурация в БД
            config_result = await db.execute(
                select(BankConfigModel).where(BankConfigModel.bank_code == bank_user_data.bank_code)
            )
            db_config = config_result.scalar_one_or_none()
            
            if not db_config:
                # Создаем конфигурацию банка в БД
                new_bank_config = BankConfigModel(
                    bank_code=bank_user_data.bank_code,
                    api_url=bank_config.api_url,
                    client_id=bank_config.client_id,
                    client_secret=bank_config.client_secret,
                    requesting_bank=bank_config.requesting_bank,
                    requesting_bank_name=bank_config.requesting_bank_name,
                    redirecting_url=bank_config.redirecting_url,
                    is_active=True
                )
                db.add(new_bank_config)
                await db.flush()
                logger.info(f"Created bank config for {bank_user_data.bank_code}")
        
        # Проверяем существование записи
        result = await db.execute(
            select(BankUser).where(
                BankUser.user_id == user_id,
                BankUser.bank_code == bank_user_data.bank_code
            )
        )
        existing_bank_user = result.scalars().first()
        
        if existing_bank_user:
            # Обновляем существующую запись
            existing_bank_user.bank_user_id = bank_user_data.bank_user_id
            await db.commit()
            await db.refresh(existing_bank_user)
            return BankUserResponse(
                id=existing_bank_user.id,
                user_id=existing_bank_user.user_id,
                bank_code=existing_bank_user.bank_code,
                bank_user_id=existing_bank_user.bank_user_id,
                created_at=existing_bank_user.created_at.isoformat(),
                updated_at=existing_bank_user.updated_at.isoformat()
            )
        else:
            # Создаем новую запись
            new_bank_user = BankUser(
                user_id=user_id,
                bank_code=bank_user_data.bank_code,
                bank_user_id=bank_user_data.bank_user_id
            )
            db.add(new_bank_user)
            await db.commit()
            await db.refresh(new_bank_user)
            return BankUserResponse(
                id=new_bank_user.id,
                user_id=new_bank_user.user_id,
                bank_code=new_bank_user.bank_code,
                bank_user_id=new_bank_user.bank_user_id,
                created_at=new_bank_user.created_at.isoformat(),
                updated_at=new_bank_user.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving bank user: {str(e)}"
        )


@router.delete("/me/bank-users/{bank_code}")
async def delete_bank_user(
    bank_code: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить bank_user_id для банка и связанные согласия"""
    try:
        from app.models import BankConsent
        from sqlalchemy import delete as sql_delete, and_
        
        result = await db.execute(
            select(BankUser).where(
                BankUser.user_id == user_id,
                BankUser.bank_code == bank_code
            )
        )
        bank_user = result.scalars().first()
        
        if not bank_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bank user not found for bank_code: {bank_code}"
            )
        
        # Отвязываем согласия от счетов перед удалением
        from app.models import BankAccount
        from sqlalchemy import update
        
        update_stmt = update(BankAccount).where(
            and_(
                BankAccount.user_id == user_id,
                BankAccount.bank_code == bank_code
            )
        ).values(consent_id=None)
        await db.execute(update_stmt)
        
        # Удаляем связанные согласия для этого банка
        consent_delete_stmt = sql_delete(BankConsent).where(
            and_(
                BankConsent.user_id == user_id,
                BankConsent.bank_code == bank_code
            )
        )
        await db.execute(consent_delete_stmt)
        logger.info(f"Deleted consents for user {user_id} and bank {bank_code}")
        
        # Удаляем bank_user
        await db.delete(bank_user)
        await db.commit()
        
        return {"message": f"Bank user and associated consents for {bank_code} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting bank user: {str(e)}"
        )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict
from app.models import User, BankUser
from app.schemas import UserResponse
from app.database import get_db
from app.security.oauth2 import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

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
    """Сохранить или обновить bank_user_id для банка"""
    try:
        # Проверяем валидность bank_code
        valid_banks = ["vbank", "abank", "sbank"]
        if bank_user_data.bank_code not in valid_banks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bank_code. Must be one of: {', '.join(valid_banks)}"
            )
        
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
    """Удалить bank_user_id для банка"""
    try:
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
        
        await db.delete(bank_user)
        await db.commit()
        
        return {"message": f"Bank user for {bank_code} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting bank user: {str(e)}"
        )

import secrets
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas import UserRegister, UserResponse, SMSVerificationRequest, SMSVerificationConfirm
from app.auth_schemas import TokenResponse, TokenRequest, RefreshTokenRequest
from app.models import User
from app.database import get_db
from app.services.sms_service import sms_service
from app.services.oauth_service import oauth_service
from app.security.password import hash_password, verify_password
from app.security.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.config import get_settings
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Регистрация пользователя"""
    
    # Проверка существования пользователя
    result = await db.execute(
        select(User).where((User.email == user_data.email) | (User.phone_number == user_data.phone_number))
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email или номер телефона уже зарегистрирован"
        )
    
    # Создание пользователя
    user = User(
        email=user_data.email,
        phone_number=user_data.phone_number,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hash_password(user_data.password),
        is_active=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Отправка SMS кода
    sms_sent = await sms_service.send_registration_code(user_data.phone_number, db)
    if not sms_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка отправки SMS"
        )
    
    return UserResponse.from_orm(user)

@router.post("/verify-sms")
async def verify_sms(data: SMSVerificationConfirm, db: AsyncSession = Depends(get_db)):
    """Проверка SMS кода"""
    
    # Проверка кода
    verified = await sms_service.verify_sms_code(data.phone_number, data.code, db)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истекший код"
        )
    
    # Обновление пользователя
    result = await db.execute(select(User).where(User.phone_number == data.phone_number))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user.is_phone_verified = True
    user.is_active = True
    await db.commit()
    
    return {"message": "Номер телефона успешно подтвержден"}

@router.post("/login", response_model=TokenResponse)
async def login(credentials: TokenRequest, db: AsyncSession = Depends(get_db)):
    """Вход в систему"""
    
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalars().first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен"
        )
    
    # Генерация токенов
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(user.id)
    
    # Обновление последнего входа
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Обновление access токена"""
    
    user_id = decode_token(request.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.get("/oauth/authorize")
async def oauth_authorize(db: AsyncSession = Depends(get_db)):
    """Инициирование OAuth flow"""
    
    oauth_state = await oauth_service.generate_oauth_state("bank", db)
    auth_url = oauth_service.generate_authorization_url(oauth_state["state"])
    
    return RedirectResponse(url=auth_url)

@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Callback от банка"""
    
    # Валидация состояния
    oauth_session = await oauth_service.validate_oauth_state(state, db)
    if not oauth_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state"
        )
    
    # Обмен кода на токен
    token_response = await oauth_service.exchange_code_for_token(
        code, 
        oauth_session["code_verifier"]
    )
    
    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token"
        )
    
    # Получение информации о пользователе
    user_info = await oauth_service.get_user_info(token_response.get("access_token"))
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info"
        )
    
    # Поиск или создание пользователя
    oauth_id = user_info.get("sub")
    result = await db.execute(
        select(User).where((User.oauth_id == oauth_id) | (User.email == user_info.get("email")))
    )
    user = result.scalars().first()
    
    if not user:
        user = User(
            email=user_info.get("email"),
            phone_number=user_info.get("phone_number", ""),
            first_name=user_info.get("given_name", ""),
            last_name=user_info.get("family_name", ""),
            oauth_provider="bank",
            oauth_id=oauth_id,
            is_active=True,
            is_phone_verified=True,
            is_email_verified=True,
            hashed_password=hash_password(secrets.token_urlsafe(32))
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Генерация токенов
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(user.id)
    
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/success?access_token={access_token}&refresh_token={refresh_token}"
    )

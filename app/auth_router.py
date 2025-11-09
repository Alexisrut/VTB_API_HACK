import secrets
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas import UserRegister, UserResponse, SMSVerificationRequest, SMSVerificationConfirm
from app.auth_schemas import TokenResponse, TokenRequest, RefreshTokenRequest
from app.models import User
from app.database import get_db
from app.services.sms_service import sms_service
from app.services.oauth_service import oauth_service
from app.services.bank_oauth_service import OAuth2BankService
from app.security.password import hash_password, verify_password
from app.security.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.config import get_settings
from app.services.universal_bank_service import universal_bank_service
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Регистрация пользователя (без SMS верификации - пользователь активируется сразу)"""
    try:
        # Проверка существования пользователя
        result = await db.execute(
            select(User).where((User.email == user_data.email) | (User.phone_number == user_data.phone_number))
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email или номер телефона уже зарегистрирован"
            )
        
        # Создание пользователя с автоматической активацией (без SMS верификации)
        user = User(
            email=user_data.email,
            phone_number=user_data.phone_number,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            hashed_password=hash_password(user_data.password),
            is_active=True,  # Автоматически активируем пользователя
            is_phone_verified=True,  # Пропускаем SMS верификацию
            is_email_verified=False  # Email верификация не требуется на данном этапе
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User registered successfully: {user.id}, email: {user.email}")
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка регистрации: {str(e)}"
        )

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
    
    if not user:
        logger.warning(f"Login attempt with non-existent email: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    logger.info(f"User found: {user.id}, is_active: {user.is_active}, hashed_password length: {len(user.hashed_password) if user.hashed_password else 0}")
    
    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Invalid password for user: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted login: {user.id}")
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

@router.get("/oauth/authorize/{bank_code}")
async def oauth_authorize(bank_code: str, db: AsyncSession = Depends(get_db)):
    """
    Инициирование OAuth flow для входа через банк
    
    Процесс:
    1. Генерируем OAuth state для безопасности
    2. Перенаправляем пользователя на страницу авторизации банка
    3. После авторизации банк перенаправит на /auth/oauth/callback
    """
    
    try:
        logger.info(f"Starting OAuth authorize flow for bank: {bank_code}")
        
        # Валидация кода банка
        try:
            bank_config = settings.get_bank_config(bank_code)
        except ValueError as e:
            logger.error(f"Invalid bank code: {bank_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bank code: {bank_code}"
            )
        
        # Генерируем OAuth state для безопасности
        oauth_state_data = await oauth_service.generate_oauth_state(f"bank_{bank_code}", db)
        state = oauth_state_data["state"]
        
        logger.info(f"Generated OAuth state: {state} for bank: {bank_code}")
        
        # Генерируем URL для перенаправления на банк
        auth_url = oauth_service.generate_authorization_url(state, bank_config)
        
        logger.info(f"Redirecting to bank authorization URL: {auth_url}")
        return RedirectResponse(url=auth_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in oauth_authorize: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth authorization failed: {str(e)}"
        )

@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    Callback от банка после авторизации пользователя
    На этом этапе мы уже имеем:
    - Данные счетов пользователя
    - Согласие на доступ
    - Информацию о пользователе
    """
    try:
        logger.info(f"OAuth callback received with state: {state}")
        
        # Валидация состояния
        oauth_session = await oauth_service.validate_oauth_state(state, db)
        if not oauth_session:
            logger.error(f"Invalid OAuth state: {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state"
            )
        
        # Обмен кода на токен у банка
        logger.info("Exchanging authorization code for token...")
        token_response = await oauth_service.exchange_code_for_token(
            code, 
            oauth_session["code_verifier"]
        )
        
        if not token_response:
            logger.error("Failed to exchange code for token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        # Получение информации о пользователе от банка
        logger.info("Retrieving user info from bank...")
        user_info = await oauth_service.get_user_info(token_response.get("access_token"))
        
        if not user_info:
            logger.error("Failed to get user info")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        # Поиск или создание пользователя
        oauth_id = user_info.get("sub")
        logger.info(f"Looking up user with oauth_id: {oauth_id}")
        
        result = await db.execute(
            select(User).where((User.oauth_id == oauth_id) | (User.email == user_info.get("email")))
        )
        user = result.scalars().first()
        
        if not user:
            logger.info(f"Creating new user from OAuth info")
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
            logger.info(f"New user created: {user.id}")
        else:
            logger.info(f"Existing user found: {user.id}")
        
        # Генерация токенов
        logger.info("Generating access and refresh tokens...")
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token(user.id)
        
        logger.info(f"OAuth callback completed successfully for user {user.id}")
        
        # Перенаправление на фронтенд с токенами
        redirect_url = f"{settings.FRONTEND_URL}/auth/success?access_token={access_token}&refresh_token={refresh_token}"
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in oauth_callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )

@router.get("/oauth/bank-bills")
async def get_oauth_bank_accounts(
    bank_code: str = Query(..., description="Код банка: vbank, abank, sbank"),
    db: AsyncSession = Depends(get_db)
):
    """
    Эндпоинт для получения банковских счетов пользователя через OAuth
    Использует полный цикл получения данных от банка
    """
    try:
        logger.info(f"Getting bank accounts through full OAuth cycle for bank: {bank_code}")
        
        # Создаем экземпляр сервиса для конкретного банка
        oauth_bank_service = OAuth2BankService(bank_code=bank_code)
        
        # Можно передать реальный user_id вместо session_id
        session_id = secrets.token_urlsafe(16)
        
        bank_data = await oauth_bank_service.get_bank_accounts_full_cycle(session_id)
        
        if not bank_data.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=bank_data.get("error")
            )
        
        return {
            "success": True,
            "accounts": bank_data.get("bills", []),
            "consent_id": bank_data.get("consent_id"),
            "auto_approved": bank_data.get("auto_approved", True)
        }
        
    except Exception as e:
        logger.error(f"Error getting bank accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bank accounts: {str(e)}"
        )
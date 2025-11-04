import secrets
import aiohttp
from datetime import datetime, timedelta
from urllib.parse import urlencode
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models import OAuthSession
from sqlalchemy import select

settings = get_settings()

class OAuth2Service:
    
    async def generate_oauth_state(self, provider: str, db: AsyncSession) -> dict:
        """Генерация состояния для OAuth flow"""
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(32)
        
        oauth_session = OAuthSession(
            state=state,
            code_verifier=code_verifier,
            provider=provider,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.add(oauth_session)
        await db.commit()
        
        return {
            "state": state,
            "code_verifier": code_verifier
        }
    
    def generate_authorization_url(self, state: str) -> str:
        """Генерация URL для перенаправления на банковский API"""
        
        params = {
            "response_type": "code",
            "client_id": settings.BANK_CLIENT_ID,
            "redirect_uri": settings.BANK_REDIRECT_URI,
            "scope": "openid profile accounts",
            "state": state,
            "nonce": secrets.token_urlsafe(16),
            "code_challenge_method": "S256",
        }
        
        return f"{settings.BANK_API_URL}/oauth/authorize?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, code_verifier: str) -> dict:
        """Обмен кода на токен"""
        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.BANK_CLIENT_ID,
                "client_secret": settings.BANK_CLIENT_SECRET,
                "redirect_uri": settings.BANK_REDIRECT_URI,
                "code_verifier": code_verifier
            }
            
            async with session.post(
                f"{settings.BANK_API_URL}/oauth/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    async def get_user_info(self, access_token: str) -> dict:
        """Получение информации о пользователе"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(
                f"{settings.BANK_API_URL}/oauth/userinfo",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    async def validate_oauth_state(self, state: str, db: AsyncSession) -> dict:
        """Валидация состояния OAuth"""
        result = await db.execute(
            select(OAuthSession).where(
                OAuthSession.state == state,
                OAuthSession.expires_at > datetime.utcnow()
            )
        )
        session = result.scalars().first()
        
        if not session:
            return None
        
        return {
            "state": session.state,
            "code_verifier": session.code_verifier,
            "provider": session.provider
        }

oauth_service = OAuth2Service()

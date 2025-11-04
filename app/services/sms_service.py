import aiohttp
import random
from datetime import datetime, timedelta
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SMSVerification
from sqlalchemy import select

settings = get_settings()

class SMSService:
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Отправка SMS через API"""
        try:
            if settings.SMS_SERVICE_PROVIDER == "sms_ru":
                return await self._send_sms_ru(phone_number, message)
            return True
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    async def _send_sms_ru(self, phone_number: str, message: str) -> bool:
        """SMS через sms.ru"""
        async with aiohttp.ClientSession() as session:
            data = {
                "api_id": settings.SMS_API_KEY,
                "to": phone_number.lstrip("+"),
                "msg": message,
                "json": 1
            }
            async with session.post("https://sms.ru/sms/send", data=data) as resp:
                result = await resp.json()
                return result.get("status") == "OK"
    
    async def generate_sms_code(self) -> str:
        """Генерация 6-значного кода"""
        return "".join([str(random.randint(0, 9)) for _ in range(6)])
    
    async def send_registration_code(self, phone_number: str, db: AsyncSession) -> bool:
        """Отправка кода регистрации"""
        code = await self.generate_sms_code()
        
        # Сохранить в БД
        sms_verification = SMSVerification(
            phone_number=phone_number,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.add(sms_verification)
        await db.commit()
        
        message = f"Ваш код подтверждения: {code}. Действителен 10 минут."
        return await self.send_sms(phone_number, message)
    
    async def verify_sms_code(self, phone_number: str, code: str, db: AsyncSession) -> bool:
        """Проверка SMS кода"""
        result = await db.execute(
            select(SMSVerification).where(
                SMSVerification.phone_number == phone_number
            ).order_by(SMSVerification.created_at.desc())
        )
        verification = result.scalars().first()
        
        if not verification:
            return False
        
        if verification.expires_at < datetime.utcnow():
            return False
        
        if verification.attempts >= 3:
            return False
        
        if verification.code != code:
            verification.attempts += 1
            await db.commit()
            return False
        
        verification.verified = True
        await db.commit()
        return True

sms_service = SMSService()

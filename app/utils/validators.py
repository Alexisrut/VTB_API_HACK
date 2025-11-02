import re

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Проверка надежности пароля"""
    if len(password) < 8:
        return False, "Пароль должен быть минимум 8 символов"
    
    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать заглавные буквы"
    
    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать строчные буквы"
    
    if not re.search(r'\d', password):
        return False, "Пароль должен содержать цифры"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Пароль должен содержать спецсимволы"
    
    return True, "OK"

def validate_email_format(email: str) -> bool:
    """Проверка формата email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone_format(phone: str) -> bool:
    """Проверка формата телефона"""
    pattern = r'^\+7\d{10}$'
    return re.match(pattern, phone) is not None

def is_email_valid(email: str) -> bool:
    """Расширенная проверка email"""
    return validate_email_format(email)

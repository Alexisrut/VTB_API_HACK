from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    
    sms_code = Column(String(6), nullable=True)
    sms_code_expires_at = Column(DateTime, nullable=True)
    sms_attempts = Column(Integer, default=0)
    
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SMSVerification(Base):
    __tablename__ = "sms_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    code = Column(String(6), nullable=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class OAuthSession(Base):
    __tablename__ = "oauth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(255), unique=True, nullable=False)
    code_verifier = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class AccessTokenBlacklist(Base):
    __tablename__ = "access_token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(1000), unique=True, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== FINANCIAL DATA MODELS ====================

class BankConsent(Base):
    """Хранение согласий на доступ к банковским данным"""
    __tablename__ = "bank_consents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bank_code = Column(String(50), nullable=False, index=True)  # vbank, abank, sbank
    consent_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="approved")  # approved, pending, revoked
    auto_approved = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (Index('ix_user_bank_consent', 'user_id', 'bank_code'),)


class BankAccount(Base):
    """Хранение банковских счетов пользователя"""
    __tablename__ = "bank_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bank_code = Column(String(50), nullable=False, index=True)
    account_id = Column(String(255), nullable=False)  # ID счета в банке
    consent_id = Column(String(255), ForeignKey("bank_consents.consent_id"), nullable=True)
    
    # Данные счета
    account_type = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=True, default="RUB")
    account_name = Column(String(255), nullable=True)
    iban = Column(String(50), nullable=True)
    bic = Column(String(50), nullable=True)
    
    # Баланс
    current_balance = Column(Numeric(15, 2), nullable=True)
    available_balance = Column(Numeric(15, 2), nullable=True)
    balance_updated_at = Column(DateTime, nullable=True)
    
    # Метаданные
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_user_bank_account', 'user_id', 'bank_code', 'account_id'),
    )


class BankTransaction(Base):
    """Хранение банковских транзакций"""
    __tablename__ = "bank_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False, index=True)
    bank_code = Column(String(50), nullable=False, index=True)
    
    # Данные транзакции
    transaction_id = Column(String(255), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=True, default="RUB")
    transaction_type = Column(String(50), nullable=True)  # debit, credit
    booking_date = Column(DateTime, nullable=False, index=True)
    value_date = Column(DateTime, nullable=True)
    
    # Детали платежа
    remittance_information = Column(Text, nullable=True)  # Назначение платежа
    creditor_name = Column(String(255), nullable=True)
    creditor_account = Column(String(255), nullable=True)
    debtor_name = Column(String(255), nullable=True)
    debtor_account = Column(String(255), nullable=True)
    
    # Категоризация (для аналитики)
    category = Column(String(100), nullable=True, index=True)  # income, expense, transfer
    subcategory = Column(String(100), nullable=True)
    counterparty_id = Column(Integer, ForeignKey("counterparties.id"), nullable=True, index=True)
    
    # Метаданные
    is_processed = Column(Boolean, default=False)  # Обработана ли для аналитики
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_user_date_transaction', 'user_id', 'booking_date'),
        Index('ix_account_date_transaction', 'account_id', 'booking_date'),
    )


class Counterparty(Base):
    """Контрагенты (клиенты и поставщики)"""
    __tablename__ = "counterparties"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Основная информация
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, index=True)  # customer, supplier, other
    inn = Column(String(20), nullable=True)  # ИНН
    kpp = Column(String(20), nullable=True)  # КПП
    
    # Контакты
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Банковские реквизиты
    account_number = Column(String(50), nullable=True)
    bank_name = Column(String(255), nullable=True)
    bic = Column(String(50), nullable=True)
    correspondent_account = Column(String(50), nullable=True)
    
    # Статистика
    total_received = Column(Numeric(15, 2), default=0)  # Всего получено от контрагента
    total_paid = Column(Numeric(15, 2), default=0)  # Всего выплачено контрагенту
    transaction_count = Column(Integer, default=0)
    
    # Метаданные
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_user_type_counterparty', 'user_id', 'type'),
    )


class AccountsReceivable(Base):
    """Дебиторская задолженность (счета к получению)"""
    __tablename__ = "accounts_receivable"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    counterparty_id = Column(Integer, ForeignKey("counterparties.id"), nullable=False, index=True)
    
    # Данные счета
    invoice_number = Column(String(100), nullable=False)
    invoice_date = Column(DateTime, nullable=False, index=True)
    due_date = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=True, default="RUB")
    
    # Статус
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, partial, paid, overdue, cancelled
    paid_amount = Column(Numeric(15, 2), default=0)
    
    # Описание
    description = Column(Text, nullable=True)
    
    # Автоматизация
    auto_reminder_enabled = Column(Boolean, default=True)
    last_reminder_sent = Column(DateTime, nullable=True)
    reminder_days_before = Column(Integer, default=3)  # За сколько дней напоминать
    
    # Связь с транзакцией оплаты
    payment_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_user_status_ar', 'user_id', 'status'),
        Index('ix_due_date_status', 'due_date', 'status'),
    )


class CashFlowPrediction(Base):
    """Прогнозы денежных потоков (ML predictions)"""
    __tablename__ = "cash_flow_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Период прогноза
    prediction_date = Column(DateTime, nullable=False, index=True)  # Дата, на которую прогноз
    prediction_created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Прогнозируемые значения
    predicted_inflow = Column(Numeric(15, 2), nullable=False)  # Прогнозируемый приток
    predicted_outflow = Column(Numeric(15, 2), nullable=False)  # Прогнозируемый отток
    predicted_balance = Column(Numeric(15, 2), nullable=False)  # Прогнозируемый баланс
    
    # Вероятность дефицита
    gap_probability = Column(Numeric(5, 2), nullable=True)  # Вероятность кассового разрыва (0-100)
    gap_amount = Column(Numeric(15, 2), nullable=True)  # Размер возможного разрыва
    
    # Модель и метрики
    model_version = Column(String(50), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)  # Уверенность модели (0-100)
    
    # Фактические значения (для оценки точности)
    actual_inflow = Column(Numeric(15, 2), nullable=True)
    actual_outflow = Column(Numeric(15, 2), nullable=True)
    actual_balance = Column(Numeric(15, 2), nullable=True)
    
    __table_args__ = (
        Index('ix_user_prediction_date', 'user_id', 'prediction_date'),
    )


class FinancialHealthMetrics(Base):
    """Метрики финансового здоровья"""
    __tablename__ = "financial_health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Период расчета
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Доходы и расходы
    total_revenue = Column(Numeric(15, 2), default=0)
    total_expenses = Column(Numeric(15, 2), default=0)
    net_income = Column(Numeric(15, 2), default=0)
    
    # Балансы
    total_assets = Column(Numeric(15, 2), default=0)
    total_liabilities = Column(Numeric(15, 2), default=0)
    net_worth = Column(Numeric(15, 2), default=0)
    
    # Метрики ликвидности
    current_ratio = Column(Numeric(10, 2), nullable=True)  # Коэффициент текущей ликвидности
    quick_ratio = Column(Numeric(10, 2), nullable=True)  # Коэффициент быстрой ликвидности
    
    # Метрики дебиторской задолженности
    total_ar = Column(Numeric(15, 2), default=0)  # Общая дебиторская задолженность
    overdue_ar = Column(Numeric(15, 2), default=0)  # Просроченная ДЗ
    ar_turnover_days = Column(Numeric(10, 2), nullable=True)  # Оборачиваемость ДЗ в днях
    
    # Метрики денежного потока
    operating_cash_flow = Column(Numeric(15, 2), default=0)
    cash_flow_trend = Column(String(50), nullable=True)  # increasing, decreasing, stable
    
    # Общий health score (0-100)
    health_score = Column(Integer, nullable=True)  # 0-100
    health_status = Column(String(50), nullable=True)  # excellent, good, fair, poor, critical
    
    # Дополнительные метрики (JSON для гибкости)
    additional_metrics = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('ix_user_period_metrics', 'user_id', 'period_start', 'period_end'),
    )

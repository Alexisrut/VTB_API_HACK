from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class BankAccountSchema(BaseModel):
    """Схема банковского счета"""
    account_id: str = Field(..., description="ID счета")
    account_type: Optional[str] = Field(None, description="Тип счета")
    currency: Optional[str] = Field(None, description="Валюта")
    account_name: Optional[str] = Field(None, description="Название счета")
    iban: Optional[str] = Field(None, description="IBAN")
    bic: Optional[str] = Field(None, description="BIC")
    
    class Config:
        from_attributes = True


class BankBalanceSchema(BaseModel):
    """Схема баланса счета"""
    account_id: str = Field(..., description="ID счета")
    balance_amount: Optional[float] = Field(None, description="Сумма баланса")
    currency: Optional[str] = Field(None, description="Валюта")
    balance_type: Optional[str] = Field(None, description="Тип баланса")
    date_time: Optional[datetime] = Field(None, description="Дата и время")
    
    class Config:
        from_attributes = True


class BankTransactionSchema(BaseModel):
    """Схема банковской транзакции"""
    transaction_id: Optional[str] = Field(None, description="ID транзакции")
    account_id: str = Field(..., description="ID счета")
    amount: Optional[float] = Field(None, description="Сумма транзакции")
    currency: Optional[str] = Field(None, description="Валюта")
    transaction_type: Optional[str] = Field(None, description="Тип транзакции")
    booking_date: Optional[datetime] = Field(None, description="Дата транзакции")
    value_date: Optional[datetime] = Field(None, description="Дата валютирования")
    remittance_information: Optional[str] = Field(None, description="Назначение платежа")
    creditor_name: Optional[str] = Field(None, description="Имя получателя")
    creditor_account: Optional[str] = Field(None, description="Счет получателя")
    debtor_name: Optional[str] = Field(None, description="Имя плательщика")
    debtor_account: Optional[str] = Field(None, description="Счет плательщика")
    
    class Config:
        from_attributes = True


class GetBankAccountsResponse(BaseModel):
    """Ответ на запрос списка счетов"""
    success: bool = Field(..., description="Успешность операции")
    accounts: List[BankAccountSchema] = Field(default_factory=list, description="Список счетов")
    consent_id: Optional[str] = Field(None, description="ID согласия")
    auto_approved: Optional[bool] = Field(None, description="Автоматически одобрено")
    
    class Config:
        from_attributes = True


class GetBankTransactionsResponse(BaseModel):
    """Ответ на запрос транзакций"""
    success: bool = Field(..., description="Успешность операции")
    account_id: str = Field(..., description="ID счета")
    transactions: List[BankTransactionSchema] = Field(default_factory=list, description="Список транзакций")
    total_count: int = Field(..., description="Общее количество транзакций")
    
    class Config:
        from_attributes = True


class GetBankBalanceHistoryResponse(BaseModel):
    """Ответ на запрос истории балансов"""
    success: bool = Field(..., description="Успешность операции")
    account_id: str = Field(..., description="ID счета")
    balances: List[BankBalanceSchema] = Field(default_factory=list, description="История балансов")
    
    class Config:
        from_attributes = True


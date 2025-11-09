from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class BalanceAmount(BaseModel):
    amount: str
    currency: str


class BankBalanceSchema(BaseModel):
    balanceAmount: BalanceAmount
    balanceType: str
    creditDebitIndicator: str


class AccountDetails(BaseModel):
    schemeName: Optional[str] = None
    identification: Optional[str] = None
    name: Optional[str] = None
    secondaryIdentification: Optional[str] = None


class BankAccountSchema(BaseModel):
    account_id: str
    account_type: Optional[str] = None
    currency: Optional[str] = None
    nickname: Optional[str] = None
    account: Optional[AccountDetails] = None
    balances: Optional[List[BankBalanceSchema]] = None


class GetBankAccountsResponse(BaseModel):
    success: bool
    accounts: List[BankAccountSchema]
    consent_id: Optional[str] = None
    auto_approved: Optional[bool] = None


class TransactionAmount(BaseModel):
    amount: str
    currency: str


class RemittanceInformation(BaseModel):
    unstructured: Optional[str] = None


class BankTransactionSchema(BaseModel):
    transactionId: str
    transactionReference: Optional[str] = None
    amount: TransactionAmount
    creditDebitIndicator: str
    status: str
    bookingDateTime: Optional[str] = None
    valueDateTime: Optional[str] = None
    transactionInformation: Optional[str] = None
    creditorName: Optional[str] = None
    debtorName: Optional[str] = None
    remittanceInformation: Optional[RemittanceInformation] = None


class GetBankTransactionsResponse(BaseModel):
    success: bool
    account_id: str
    transactions: List[BankTransactionSchema]
    total_count: int


class GetBankBalanceHistoryResponse(BaseModel):
    success: bool
    account_id: str
    balances: List[BankBalanceSchema]


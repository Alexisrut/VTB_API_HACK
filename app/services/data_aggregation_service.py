"""
Сервис для агрегации и синхронизации данных из банков
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from app.models import (
    BankAccount, BankTransaction, BankConsent, 
    User, Counterparty
)
from app.services.universal_bank_service import universal_bank_service

logger = logging.getLogger(__name__)


class DataAggregationService:
    """Сервис для синхронизации данных из банков"""
    
    def __init__(self):
        self.bank_service = universal_bank_service
    
    async def sync_user_accounts(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: Optional[str] = None
    ) -> Dict:
        """
        Синхронизировать счета пользователя из банков
        
        Args:
            db: Database session
            user_id: ID пользователя
            bank_code: Код банка (если None - все банки)
        
        Returns:
            dict: Результат синхронизации
        """
        try:
            bank_codes = [bank_code] if bank_code else ["vbank", "abank", "sbank"]
            results = {}
            
            for bank_code in bank_codes:
                try:
                    # Получаем данные из банка (используя bank_user_id из БД если доступен)
                    bank_result = await self.bank_service.get_all_accounts_full_cycle(
                        bank_code=bank_code,
                        user_id=str(user_id),  # Fallback если нет bank_user_id в БД
                        db=db,
                        internal_user_id=user_id
                    )
                    
                    if not bank_result.get("success"):
                        error_msg = bank_result.get("error", "Unknown error")
                        # Проверяем, не связана ли ошибка с отсутствием bank_user_id
                        if "No bank_user_id" in error_msg or "bank_user_id" in error_msg.lower():
                            results[bank_code] = {
                                "success": False,
                                "error": f"{error_msg}. Please set bank_user_id in your profile first."
                            }
                        else:
                            results[bank_code] = {
                                "success": False,
                                "error": error_msg
                            }
                        continue
                    
                    # Сохраняем согласие
                    consent_id = bank_result.get("consent_id")
                    if consent_id:
                        await self._save_consent(
                            db=db,
                            user_id=user_id,
                            bank_code=bank_code,
                            consent_id=consent_id,
                            auto_approved=bank_result.get("auto_approved", True)
                        )
                    
                    # Сохраняем счета
                    accounts = bank_result.get("accounts", [])
                    saved_count = 0
                    for account_data in accounts:
                        account_id = account_data.get("account_id") or account_data.get("id")
                        if not account_id:
                            continue
                        
                        await self._save_account(
                            db=db,
                            user_id=user_id,
                            bank_code=bank_code,
                            account_id=account_id,
                            account_data=account_data,
                            consent_id=consent_id
                        )
                        saved_count += 1
                    
                    results[bank_code] = {
                        "success": True,
                        "accounts_synced": saved_count
                    }
                    
                except Exception as e:
                    logger.error(f"Error syncing {bank_code} for user {user_id}: {e}")
                    results[bank_code] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in sync_user_accounts: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def fetch_and_save_accounts(
        self,
        bank_code: str,
        user_id: int,
        db: AsyncSession
    ) -> Dict:
        """
        Получить счета из банка и сохранить их в БД.
        Используется для endpoint GET /accounts.
        """
        try:
            # Получаем данные из банка
            bank_result = await self.bank_service.get_all_accounts_full_cycle(
                bank_code=bank_code,
                user_id=str(user_id),
                db=db,
                internal_user_id=user_id
            )
            
            if not bank_result.get("success"):
                return bank_result
            
            # Сохраняем согласие
            consent_id = bank_result.get("consent_id")
            if consent_id:
                await self._save_consent(
                    db=db,
                    user_id=user_id,
                    bank_code=bank_code,
                    consent_id=consent_id,
                    auto_approved=bank_result.get("auto_approved", True)
                )
            
            # Сохраняем счета
            accounts = bank_result.get("accounts", [])
            for account_data in accounts:
                account_id = account_data.get("account_id") or account_data.get("id")
                if not account_id:
                    continue
                
                await self._save_account(
                    db=db,
                    user_id=user_id,
                    bank_code=bank_code,
                    account_id=account_id,
                    account_data=account_data,
                    consent_id=consent_id
                )
            
            return bank_result
            
        except Exception as e:
            logger.error(f"Error in fetch_and_save_accounts: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def sync_account_transactions(
        self,
        db: AsyncSession,
        user_id: int,
        account_id: int,
        bank_code: str,
        consent_id: str,
        days_back: int = 90
    ) -> Dict:
        """
        Синхронизировать транзакции по счету
        
        Args:
            db: Database session
            user_id: ID пользователя
            account_id: ID счета в нашей БД
            bank_code: Код банка
            consent_id: ID согласия
            days_back: За сколько дней назад получать транзакции
        
        Returns:
            dict: Результат синхронизации
        """
        try:
            # Получаем account_id из банка
            account = await db.get(BankAccount, account_id)
            if not account:
                return {"success": False, "error": "Account not found"}
            
            bank_account_id = account.account_id
            
            # Получаем токен банка
            access_token = await self.bank_service.get_bank_access_token(bank_code)
            if not access_token:
                return {"success": False, "error": "Failed to get bank token"}
            
            # Вычисляем даты
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=days_back)
            
            # Получаем транзакции из банка
            # Преобразуем даты в формат ISO 8601
            from_booking_date_time = from_date.strftime("%Y-%m-%dT00:00:00Z")
            to_booking_date_time = to_date.strftime("%Y-%m-%dT23:59:59Z")
            
            transactions_data = await self.bank_service.get_account_transactions(
                bank_code=bank_code,
                access_token=access_token,
                account_id=bank_account_id,
                consent_id=consent_id,
                from_booking_date_time=from_booking_date_time,
                to_booking_date_time=to_booking_date_time,
                page=None,  # Получаем все транзакции без пагинации при синхронизации
                limit=None
            )
            
            if not transactions_data:
                return {"success": False, "error": "Failed to fetch transactions"}
            
            transactions = transactions_data.get("transactions", [])
            saved_count = 0
            
            for tx_data in transactions:
                await self._save_transaction(
                    db=db,
                    user_id=user_id,
                    account_id=account_id,
                    bank_code=bank_code,
                    transaction_data=tx_data
                )
                saved_count += 1
            
            # Обновляем время последней синхронизации
            account.last_synced_at = datetime.utcnow()
            await db.commit()
            
            return {
                "success": True,
                "transactions_synced": saved_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing transactions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def sync_all_accounts_transactions(
        self,
        db: AsyncSession,
        user_id: int,
        days_back: int = 90
    ) -> Dict:
        """Синхронизировать транзакции по всем счетам пользователя"""
        try:
            # Получаем все активные счета пользователя
            stmt = select(BankAccount).where(
                and_(
                    BankAccount.user_id == user_id,
                    BankAccount.is_active == True
                )
            )
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            
            results = {}
            for account in accounts:
                # Получаем согласие
                consent = await self._get_active_consent(
                    db=db,
                    user_id=user_id,
                    bank_code=account.bank_code
                )
                
                if not consent:
                    results[account.id] = {
                        "success": False,
                        "error": "No active consent"
                    }
                    continue
                
                result = await self.sync_account_transactions(
                    db=db,
                    user_id=user_id,
                    account_id=account.id,
                    bank_code=account.bank_code,
                    consent_id=consent.consent_id,
                    days_back=days_back
                )
                results[account.id] = result
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error syncing all transactions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_transactions_read_through(
        self,
        db: AsyncSession,
        user_id: int,
        account_id: str,  # Bank's account ID (string)
        bank_code: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
        ttl_seconds: int = 300  # 5 minutes cache TTL
    ) -> Dict:
        """
        Получить транзакции с использованием паттерна Read-Through Caching.
        
        1. Проверяет наличие локальных данных и их свежесть.
        2. Если данные устарели или отсутствуют, синхронизирует их с банком.
        3. Возвращает данные из локальной БД с пагинацией и фильтрацией.
        """
        try:
            # 1. Находим счет в нашей БД
            stmt = select(BankAccount).where(
                and_(
                    BankAccount.user_id == user_id,
                    BankAccount.account_id == account_id,
                    BankAccount.bank_code == bank_code
                )
            )
            result = await db.execute(stmt)
            account = result.scalar_one_or_none()
            
            if not account:
                # Попытка восстановления: Если счета нет в БД, попробуем получить его из банка
                logger.info(f"Account {account_id} not found in DB, attempting to fetch from bank...")
                
                # Нам нужен токен и согласие
                access_token = await self.bank_service.get_bank_access_token(bank_code, db=db)
                if not access_token:
                    return {"success": False, "error": "Account not found in DB and failed to get bank token"}
                
                # Ищем любое активное согласие
                consent = await self._get_active_consent(db, user_id, bank_code)
                if not consent:
                     return {"success": False, "error": "Account not found in DB and no active consent found"}
                
                # Пытаемся получить детали счета из банка
                account_data = await self.bank_service.get_account_details(
                    bank_code=bank_code,
                    access_token=access_token,
                    account_id=account_id,
                    consent_id=consent.consent_id,
                    db=db,
                    internal_user_id=user_id
                )
                
                if not account_data:
                    # Если и в банке не нашли, или ошибка
                    return {"success": False, "error": "Account not found in database and failed to fetch from bank"}
                
                # Если данные вложены в data.account или data.accounts, извлекаем
                if isinstance(account_data, dict):
                    if "data" in account_data:
                         if "account" in account_data["data"]:
                             acc_list = account_data["data"]["account"]
                             if isinstance(acc_list, list) and acc_list:
                                 account_data = acc_list[0]
                             elif isinstance(acc_list, dict):
                                 account_data = acc_list
                    elif "account" in account_data:
                        acc_list = account_data["account"]
                        if isinstance(acc_list, list) and acc_list:
                            account_data = acc_list[0]
                        elif isinstance(acc_list, dict):
                            account_data = acc_list

                # Сохраняем счет
                account = await self._save_account(
                    db=db,
                    user_id=user_id,
                    bank_code=bank_code,
                    account_id=account_id,
                    account_data=account_data,
                    consent_id=consent.consent_id
                )
                logger.info(f"Successfully recovered and saved account {account_id} to DB")

            if not account:
                 return {"success": False, "error": "Account could not be saved/retrieved"}

            # 2. Проверяем свежесть данных
            is_stale = True
            if account.last_synced_at:
                age = (datetime.utcnow() - account.last_synced_at).total_seconds()
                if age < ttl_seconds:
                    is_stale = False
                    logger.info(f"Transactions cache hit for {account_id} (age: {age}s)")
            
            # 3. Если данные устарели, синхронизируем
            if is_stale:
                logger.info(f"Transactions cache miss for {account_id} (stale), syncing...")
                
                # Получаем согласие
                consent = await self._get_active_consent(db, user_id, bank_code)
                
                if consent:
                    # Синхронизируем (по умолчанию 90 дней, или можно больше)
                    sync_result = await self.sync_account_transactions(
                        db=db,
                        user_id=user_id,
                        account_id=account.id,
                        bank_code=bank_code,
                        consent_id=consent.consent_id,
                        days_back=90 # Можно настроить
                    )
                    if not sync_result.get("success"):
                        logger.warning(f"Failed to sync transactions: {sync_result.get('error')}")
                        # Продолжаем, чтобы вернуть хотя бы старые данные
                else:
                    logger.warning(f"No active consent for {bank_code} to sync transactions")
            
            # 4. Возвращаем данные из БД
            query = select(BankTransaction).where(
                and_(
                    BankTransaction.user_id == user_id,
                    BankTransaction.account_id == account.id
                )
            )
            
            # Фильтры по дате
            if from_date:
                query = query.where(BankTransaction.booking_date >= from_date)
            if to_date:
                query = query.where(BankTransaction.booking_date <= to_date)
            
            # Сортировка
            query = query.order_by(desc(BankTransaction.booking_date))
            
            # Пагинация
            # Сначала получаем общее количество
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # Применяем limit/offset
            offset = (page - 1) * limit
            query = query.limit(limit).offset(offset)
            
            result = await db.execute(query)
            transactions = result.scalars().all()
            
            # Преобразуем в словари для совместимости
            transactions_list = []
            for tx in transactions:
                transactions_list.append({
                    "transaction_id": tx.transaction_id,
                    "accountId": account_id,
                    "account_id": account_id,
                    "amount": float(tx.amount),
                    "currency": tx.currency,
                    "transaction_type": tx.transaction_type,
                    "creditDebitIndicator": "Credit" if tx.transaction_type == "credit" else "Debit",
                    "status": "booked", # В БД храним только подтвержденные обычно
                    "booking_date": tx.booking_date,
                    "bookingDateTime": tx.booking_date.isoformat() if tx.booking_date else None,
                    "value_date": tx.value_date,
                    "valueDateTime": tx.value_date.isoformat() if tx.value_date else None,
                    "remittance_information": tx.remittance_information,
                    "transactionInformation": tx.remittance_information,
                    "creditor_name": tx.creditor_name,
                    "creditorName": tx.creditor_name,
                    "creditor_account": tx.creditor_account,
                    "debtor_name": tx.debtor_name,
                    "debtorName": tx.debtor_name,
                    "debtor_account": tx.debtor_account
                })
            
            return {
                "success": True,
                "transactions": transactions_list,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "source": "database"
            }
            
        except Exception as e:
            logger.error(f"Error in get_transactions_read_through: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def save_account(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str,
        account_id: str,
        account_data: Dict,
        consent_id: Optional[str] = None
    ):
        """Сохранить или обновить счет (публичный метод)"""
        return await self._save_account(db, user_id, bank_code, account_id, account_data, consent_id)

    # ==================== PRIVATE METHODS ====================
    
    async def _save_consent(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str,
        consent_id: str,
        auto_approved: bool = True
    ):
        """Сохранить или обновить согласие"""
        stmt = select(BankConsent).where(
            and_(
                BankConsent.user_id == user_id,
                BankConsent.bank_code == bank_code,
                BankConsent.consent_id == consent_id
            )
        )
        result = await db.execute(stmt)
        consent = result.scalar_one_or_none()
        
        if consent:
            consent.status = "approved"
            consent.auto_approved = auto_approved
            consent.updated_at = datetime.utcnow()
        else:
            consent = BankConsent(
                user_id=user_id,
                bank_code=bank_code,
                consent_id=consent_id,
                status="approved",
                auto_approved=auto_approved
            )
            db.add(consent)
        
        await db.commit()
        return consent
    
    async def _save_account(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str,
        account_id: str,
        account_data: Dict,
        consent_id: Optional[str] = None
    ):
        """Сохранить или обновить счет"""
        stmt = select(BankAccount).where(
            and_(
                BankAccount.user_id == user_id,
                BankAccount.bank_code == bank_code,
                BankAccount.account_id == account_id
            )
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        # Извлекаем баланс
        balance_data = account_data.get("balances", [])
        current_balance = None
        available_balance = None
        
        if balance_data:
            for balance in balance_data:
                balance_type = balance.get("balance_type", "").lower()
                amount = balance.get("amount", {}).get("amount") or balance.get("balance_amount")
                if amount:
                    if "current" in balance_type or "interim" in balance_type:
                        current_balance = Decimal(str(amount))
                    elif "available" in balance_type:
                        available_balance = Decimal(str(amount))
        
        if account:
            # Обновляем существующий счет
            account.account_type = account_data.get("account_type") or account.account_type
            account.currency = account_data.get("currency") or account.currency or "RUB"
            account.account_name = account_data.get("account_name") or account_data.get("name") or account.account_name
            account.iban = account_data.get("iban") or account.iban
            account.bic = account_data.get("bic") or account.bic
            account.current_balance = current_balance or account.current_balance
            account.available_balance = available_balance or account.available_balance
            account.balance_updated_at = datetime.utcnow()
            account.consent_id = consent_id or account.consent_id
            # Не обновляем last_synced_at здесь, это делается при синхронизации транзакций
            account.is_active = True
        else:
            # Создаем новый счет
            account = BankAccount(
                user_id=user_id,
                bank_code=bank_code,
                account_id=account_id,
                consent_id=consent_id,
                account_type=account_data.get("account_type"),
                currency=account_data.get("currency") or "RUB",
                account_name=account_data.get("account_name") or account_data.get("name"),
                iban=account_data.get("iban"),
                bic=account_data.get("bic"),
                current_balance=current_balance,
                available_balance=available_balance,
                balance_updated_at=datetime.utcnow(),
                last_synced_at=None # Еще не синхронизированы транзакции
            )
            db.add(account)
        
        await db.commit()
        return account
    
    async def _save_transaction(
        self,
        db: AsyncSession,
        user_id: int,
        account_id: int,
        bank_code: str,
        transaction_data: Dict
    ):
        """
        Сохранить транзакцию в базу данных
        
        Ожидаемый формат transaction_data (из банковского API):
        {
            "transactionId": "tx-vbank-00668159",
            "accountId": "acc-3704",
            "amount": {
                "amount": "383710.09",
                "currency": "RUB"
            },
            "creditDebitIndicator": "Credit",
            "status": "completed",
            "bookingDateTime": "2025-11-08T19:23:15.285567Z",
            "valueDateTime": "2025-11-08T19:23:15.285567Z",
            "transactionInformation": "Выручка",
            ...
        }
        """
        # Извлекаем transaction_id (поддерживаем оба формата: camelCase и snake_case)
        tx_id = (
            transaction_data.get("transactionId") or 
            transaction_data.get("transaction_id") or 
            transaction_data.get("id")
        )
        
        if tx_id:
            # Проверяем, существует ли уже транзакция
            stmt = select(BankTransaction).where(
                and_(
                    BankTransaction.user_id == user_id,
                    BankTransaction.transaction_id == tx_id,
                    BankTransaction.account_id == account_id
                )
            )
            result = await db.execute(stmt)
            existing_tx = result.scalar_one_or_none()
            
            if existing_tx:
                return existing_tx  # Уже существует
        
        # Извлекаем сумму из объекта amount: { amount: "383710.09", currency: "RUB" }
        amount_obj = transaction_data.get("amount", {})
        if isinstance(amount_obj, dict):
            amount_str = amount_obj.get("amount")
            currency = amount_obj.get("currency")
        else:
            amount_str = amount_obj
            currency = None
        
        if not amount_str:
            return None
        
        amount = Decimal(str(amount_str))
        currency = currency or transaction_data.get("currency") or "RUB"
        
        # Определяем тип транзакции (creditDebitIndicator из API)
        tx_type = (
            transaction_data.get("creditDebitIndicator") or 
            transaction_data.get("credit_debit_indicator") or
            transaction_data.get("transaction_type")
        )
        if not tx_type:
            # Пытаемся определить по знаку суммы
            tx_type = "credit" if amount >= 0 else "debit"
        
        # Определяем категорию
        category = "expense" if tx_type.lower() == "debit" else "income"
        
        # Парсим даты (bookingDateTime из API)
        booking_date_str = (
            transaction_data.get("bookingDateTime") or 
            transaction_data.get("booking_date")
        )
        value_date_str = (
            transaction_data.get("valueDateTime") or 
            transaction_data.get("value_date")
        )
        
        booking_date = None
        if booking_date_str:
            try:
                if isinstance(booking_date_str, str):
                    booking_date = datetime.fromisoformat(booking_date_str.replace("Z", "+00:00"))
                else:
                    booking_date = booking_date_str
            except:
                booking_date = datetime.utcnow()
        else:
            booking_date = datetime.utcnow()
        
        # Normalize timezone info (store as naive UTC)
        if booking_date and booking_date.tzinfo is not None:
            booking_date = booking_date.astimezone(timezone.utc).replace(tzinfo=None)
        
        value_date = None
        if value_date_str:
            try:
                if isinstance(value_date_str, str):
                    value_date = datetime.fromisoformat(value_date_str.replace("Z", "+00:00"))
                else:
                    value_date = value_date_str
            except:
                pass
        
        if value_date and value_date.tzinfo is not None:
            value_date = value_date.astimezone(timezone.utc).replace(tzinfo=None)
        
        # Извлекаем remittance_information (transactionInformation из API)
        remittance_info = (
            transaction_data.get("transactionInformation") or
            transaction_data.get("remittanceInformation") or
            (transaction_data.get("remittanceInformation", {}).get("unstructured") if isinstance(transaction_data.get("remittanceInformation"), dict) else None) or
            transaction_data.get("remittance_information")
        )
        
        # Извлекаем creditor/debtor информацию
        creditor_account_obj = transaction_data.get("creditorAccount", {})
        debtor_account_obj = transaction_data.get("debtorAccount", {})
        
        creditor_account = None
        if isinstance(creditor_account_obj, dict):
            creditor_account = creditor_account_obj.get("identification") or creditor_account_obj.get("iban")
        else:
            creditor_account = transaction_data.get("creditor_account")
        
        debtor_account = None
        if isinstance(debtor_account_obj, dict):
            debtor_account = debtor_account_obj.get("identification") or debtor_account_obj.get("iban")
        else:
            debtor_account = transaction_data.get("debtor_account")
        
        # Создаем транзакцию
        transaction = BankTransaction(
            user_id=user_id,
            account_id=account_id,
            bank_code=bank_code,
            transaction_id=tx_id,
            amount=abs(amount),
            currency=currency,
            transaction_type=tx_type.lower(),
            booking_date=booking_date,
            value_date=value_date,
            remittance_information=remittance_info,
            creditor_name=transaction_data.get("creditorName") or transaction_data.get("creditor_name"),
            creditor_account=creditor_account,
            debtor_name=transaction_data.get("debtorName") or transaction_data.get("debtor_name"),
            debtor_account=debtor_account,
            category=category
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        return transaction
    
    async def _get_active_consent(
        self,
        db: AsyncSession,
        user_id: int,
        bank_code: str
    ) -> Optional[BankConsent]:
        """Получить активное согласие"""
        stmt = select(BankConsent).where(
            and_(
                BankConsent.user_id == user_id,
                BankConsent.bank_code == bank_code,
                BankConsent.status == "approved"
            )
        ).order_by(BankConsent.created_at.desc())
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# Глобальный экземпляр
data_aggregation_service = DataAggregationService()

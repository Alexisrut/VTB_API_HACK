"""
Сервис для управления дебиторской задолженностью (Accounts Receivable)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models import AccountsReceivable, Counterparty, BankTransaction

logger = logging.getLogger(__name__)


class ARManagementService:
    """Сервис для управления дебиторской задолженностью"""
    
    async def create_invoice(
        self,
        db: AsyncSession,
        user_id: int,
        counterparty_id: int,
        invoice_number: str,
        invoice_date: datetime,
        due_date: datetime,
        amount: Decimal,
        currency: str = "RUB",
        description: Optional[str] = None,
        auto_reminder_enabled: bool = True,
        reminder_days_before: int = 3
    ) -> Dict:
        """
        Создать счет к получению
        
        Returns:
            dict: Созданный счет
        """
        try:
            # Проверяем существование контрагента
            counterparty = await db.get(Counterparty, counterparty_id)
            if not counterparty or counterparty.user_id != user_id:
                return {
                    "success": False,
                    "error": "Counterparty not found"
                }
            
            # Проверяем, не существует ли уже счет с таким номером
            stmt = select(AccountsReceivable).where(
                and_(
                    AccountsReceivable.user_id == user_id,
                    AccountsReceivable.invoice_number == invoice_number
                )
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return {
                    "success": False,
                    "error": "Invoice with this number already exists"
                }
            
            # Определяем статус
            status = "overdue" if due_date < datetime.utcnow() else "pending"
            
            # Создаем счет
            invoice = AccountsReceivable(
                user_id=user_id,
                counterparty_id=counterparty_id,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                amount=amount,
                currency=currency,
                description=description,
                status=status,
                auto_reminder_enabled=auto_reminder_enabled,
                reminder_days_before=reminder_days_before
            )
            
            db.add(invoice)
            await db.commit()
            await db.refresh(invoice)
            
            return {
                "success": True,
                "invoice": {
                    "id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "counterparty_name": counterparty.name,
                    "amount": float(invoice.amount),
                    "due_date": invoice.due_date.isoformat(),
                    "status": invoice.status
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def mark_as_paid(
        self,
        db: AsyncSession,
        user_id: int,
        invoice_id: int,
        paid_amount: Optional[Decimal] = None,
        payment_transaction_id: Optional[int] = None
    ) -> Dict:
        """
        Отметить счет как оплаченный
        
        Args:
            db: Database session
            user_id: ID пользователя
            invoice_id: ID счета
            paid_amount: Сумма оплаты (если None - полная оплата)
            payment_transaction_id: ID транзакции оплаты
        """
        try:
            invoice = await db.get(AccountsReceivable, invoice_id)
            if not invoice or invoice.user_id != user_id:
                return {
                    "success": False,
                    "error": "Invoice not found"
                }
            
            if paid_amount is None:
                paid_amount = invoice.amount - invoice.paid_amount
            
            invoice.paid_amount += paid_amount
            
            # Обновляем статус
            if invoice.paid_amount >= invoice.amount:
                invoice.status = "paid"
                invoice.paid_at = datetime.utcnow()
            elif invoice.paid_amount > 0:
                invoice.status = "partial"
            
            if payment_transaction_id:
                invoice.payment_transaction_id = payment_transaction_id
            
            await db.commit()
            await db.refresh(invoice)
            
            return {
                "success": True,
                "invoice": {
                    "id": invoice.id,
                    "status": invoice.status,
                    "paid_amount": float(invoice.paid_amount),
                    "remaining_amount": float(invoice.amount - invoice.paid_amount)
                }
            }
            
        except Exception as e:
            logger.error(f"Error marking invoice as paid: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def auto_match_payments(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """
        Автоматически сопоставить входящие платежи со счетами
        
        Returns:
            dict: Результат сопоставления
        """
        try:
            # Получаем неоплаченные счета
            stmt = select(AccountsReceivable).where(
                and_(
                    AccountsReceivable.user_id == user_id,
                    AccountsReceivable.status.in_(["pending", "partial"]),
                    AccountsReceivable.payment_transaction_id.is_(None)
                )
            )
            result = await db.execute(stmt)
            unpaid_invoices = result.scalars().all()
            
            # Получаем входящие транзакции без привязки к счетам
            tx_stmt = select(BankTransaction).where(
                and_(
                    BankTransaction.user_id == user_id,
                    BankTransaction.category == "income",
                    BankTransaction.counterparty_id.isnot(None)
                )
            ).order_by(BankTransaction.booking_date.desc())
            
            tx_result = await db.execute(tx_stmt)
            income_transactions = tx_result.scalars().all()
            
            matched_count = 0
            
            for invoice in unpaid_invoices:
                remaining = invoice.amount - invoice.paid_amount
                
                # Ищем транзакцию от того же контрагента с похожей суммой
                for tx in income_transactions:
                    if tx.counterparty_id == invoice.counterparty_id:
                        # Проверяем сумму (допускаем небольшую погрешность)
                        if abs(float(tx.amount) - float(remaining)) < 0.01:
                            # Сопоставляем
                            invoice.paid_amount = invoice.amount
                            invoice.status = "paid"
                            invoice.payment_transaction_id = tx.id
                            invoice.paid_at = tx.booking_date
                            matched_count += 1
                            break
            
            await db.commit()
            
            return {
                "success": True,
                "matched_invoices": matched_count
            }
            
        except Exception as e:
            logger.error(f"Error auto-matching payments: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_overdue_invoices(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """Получить просроченные счета"""
        try:
            now = datetime.utcnow()
            
            stmt = select(AccountsReceivable).where(
                and_(
                    AccountsReceivable.user_id == user_id,
                    AccountsReceivable.status.in_(["pending", "partial"]),
                    AccountsReceivable.due_date < now
                )
            ).order_by(AccountsReceivable.due_date)
            
            result = await db.execute(stmt)
            overdue = result.scalars().all()
            
            # Обновляем статус на overdue
            for invoice in overdue:
                if invoice.status != "overdue":
                    invoice.status = "overdue"
            
            await db.commit()
            
            return {
                "success": True,
                "overdue_invoices": [
                    {
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "counterparty_id": inv.counterparty_id,
                        "amount": float(inv.amount),
                        "paid_amount": float(inv.paid_amount),
                        "remaining": float(inv.amount - inv.paid_amount),
                        "due_date": inv.due_date.isoformat(),
                        "days_overdue": (now - inv.due_date).days
                    }
                    for inv in overdue
                ],
                "total_overdue": sum(
                    float(inv.amount - inv.paid_amount)
                    for inv in overdue
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting overdue invoices: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_ar_summary(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """Получить сводку по дебиторской задолженности"""
        try:
            stmt = select(AccountsReceivable).where(
                AccountsReceivable.user_id == user_id
            )
            result = await db.execute(stmt)
            all_invoices = result.scalars().all()
            
            total_ar = sum(
                inv.amount - inv.paid_amount
                for inv in all_invoices
                if inv.status != "paid"
            )
            
            overdue_ar = sum(
                inv.amount - inv.paid_amount
                for inv in all_invoices
                if inv.status == "overdue" or (inv.due_date < datetime.utcnow() and inv.status != "paid")
            )
            
            pending_count = len([inv for inv in all_invoices if inv.status == "pending"])
            overdue_count = len([inv for inv in all_invoices if inv.status == "overdue"])
            
            return {
                "success": True,
                "summary": {
                    "total_ar": float(total_ar),
                    "overdue_ar": float(overdue_ar),
                    "pending_count": pending_count,
                    "overdue_count": overdue_count,
                    "total_invoices": len(all_invoices)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting AR summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_invoices(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        counterparty_id: Optional[int] = None
    ) -> Dict:
        """Получить список счетов"""
        try:
            conditions = [AccountsReceivable.user_id == user_id]
            
            if status:
                conditions.append(AccountsReceivable.status == status)
            
            if counterparty_id:
                conditions.append(AccountsReceivable.counterparty_id == counterparty_id)
            
            stmt = select(AccountsReceivable).where(
                and_(*conditions)
            ).order_by(AccountsReceivable.due_date.desc())
            
            result = await db.execute(stmt)
            invoices = result.scalars().all()
            
            return {
                "success": True,
                "invoices": [
                    {
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "counterparty_id": inv.counterparty_id,
                        "amount": float(inv.amount),
                        "paid_amount": float(inv.paid_amount),
                        "remaining": float(inv.amount - inv.paid_amount),
                        "invoice_date": inv.invoice_date.isoformat(),
                        "due_date": inv.due_date.isoformat(),
                        "status": inv.status,
                        "description": inv.description
                    }
                    for inv in invoices
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting invoices: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Глобальный экземпляр
ar_management_service = ARManagementService()


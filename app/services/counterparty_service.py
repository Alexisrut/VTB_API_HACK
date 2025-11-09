"""
Сервис для управления контрагентами
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models import Counterparty, BankTransaction, AccountsReceivable

logger = logging.getLogger(__name__)


class CounterpartyService:
    """Сервис для управления контрагентами"""
    
    async def create_counterparty(
        self,
        db: AsyncSession,
        user_id: int,
        name: str,
        type: str,  # customer, supplier, other
        inn: Optional[str] = None,
        kpp: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        account_number: Optional[str] = None,
        bank_name: Optional[str] = None,
        bic: Optional[str] = None,
        correspondent_account: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Создать контрагента
        
        Returns:
            dict: Созданный контрагент
        """
        try:
            if type not in ["customer", "supplier", "other"]:
                return {
                    "success": False,
                    "error": "Invalid type. Must be: customer, supplier, other"
                }
            
            counterparty = Counterparty(
                user_id=user_id,
                name=name,
                type=type,
                inn=inn,
                kpp=kpp,
                email=email,
                phone=phone,
                account_number=account_number,
                bank_name=bank_name,
                bic=bic,
                correspondent_account=correspondent_account,
                notes=notes
            )
            
            db.add(counterparty)
            await db.commit()
            await db.refresh(counterparty)
            
            return {
                "success": True,
                "counterparty": {
                    "id": counterparty.id,
                    "name": counterparty.name,
                    "type": counterparty.type
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating counterparty: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_counterparty(
        self,
        db: AsyncSession,
        user_id: int,
        counterparty_id: int,
        **kwargs
    ) -> Dict:
        """Обновить данные контрагента"""
        try:
            counterparty = await db.get(Counterparty, counterparty_id)
            if not counterparty or counterparty.user_id != user_id:
                return {
                    "success": False,
                    "error": "Counterparty not found"
                }
            
            # Обновляем только переданные поля
            allowed_fields = [
                "name", "type", "inn", "kpp", "email", "phone",
                "account_number", "bank_name", "bic", "correspondent_account",
                "notes", "is_active"
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(counterparty, field):
                    setattr(counterparty, field, value)
            
            counterparty.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(counterparty)
            
            return {
                "success": True,
                "counterparty": self._format_counterparty(counterparty)
            }
            
        except Exception as e:
            logger.error(f"Error updating counterparty: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_counterparty(
        self,
        db: AsyncSession,
        user_id: int,
        counterparty_id: int
    ) -> Dict:
        """Получить контрагента с деталями"""
        try:
            counterparty = await db.get(Counterparty, counterparty_id)
            if not counterparty or counterparty.user_id != user_id:
                return {
                    "success": False,
                    "error": "Counterparty not found"
                }
            
            # Получаем статистику транзакций
            stats = await self._get_counterparty_stats(db, counterparty_id)
            
            return {
                "success": True,
                "counterparty": {
                    **self._format_counterparty(counterparty),
                    "statistics": stats
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting counterparty: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_counterparties(
        self,
        db: AsyncSession,
        user_id: int,
        type: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict:
        """Получить список контрагентов"""
        try:
            conditions = [Counterparty.user_id == user_id]
            
            if type:
                conditions.append(Counterparty.type == type)
            
            if search:
                conditions.append(
                    Counterparty.name.ilike(f"%{search}%")
                )
            
            stmt = select(Counterparty).where(
                and_(*conditions)
            ).order_by(Counterparty.name)
            
            result = await db.execute(stmt)
            counterparties = result.scalars().all()
            
            return {
                "success": True,
                "counterparties": [
                    self._format_counterparty(cp)
                    for cp in counterparties
                ]
            }
            
        except Exception as e:
            logger.error(f"Error listing counterparties: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def auto_create_from_transaction(
        self,
        db: AsyncSession,
        user_id: int,
        transaction_id: int
    ) -> Dict:
        """
        Автоматически создать контрагента из транзакции
        
        Returns:
            dict: Созданный контрагент
        """
        try:
            transaction = await db.get(BankTransaction, transaction_id)
            if not transaction or transaction.user_id != user_id:
                return {
                    "success": False,
                    "error": "Transaction not found"
                }
            
            # Определяем тип контрагента
            if transaction.category == "income":
                cp_type = "customer"
                name = transaction.creditor_name or "Unknown Customer"
            else:
                cp_type = "supplier"
                name = transaction.debtor_name or "Unknown Supplier"
            
            # Проверяем, не существует ли уже такой контрагент
            stmt = select(Counterparty).where(
                and_(
                    Counterparty.user_id == user_id,
                    Counterparty.name == name
                )
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Привязываем транзакцию к существующему контрагенту
                transaction.counterparty_id = existing.id
                await db.commit()
                return {
                    "success": True,
                    "counterparty": self._format_counterparty(existing),
                    "created": False
                }
            
            # Создаем нового контрагента
            counterparty = Counterparty(
                user_id=user_id,
                name=name,
                type=cp_type,
                account_number=transaction.creditor_account if cp_type == "customer" else transaction.debtor_account
            )
            
            db.add(counterparty)
            await db.commit()
            await db.refresh(counterparty)
            
            # Привязываем транзакцию
            transaction.counterparty_id = counterparty.id
            await db.commit()
            
            return {
                "success": True,
                "counterparty": self._format_counterparty(counterparty),
                "created": True
            }
            
        except Exception as e:
            logger.error(f"Error auto-creating counterparty: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_counterparty_stats(
        self,
        db: AsyncSession,
        counterparty_id: int
    ):
        """Обновить статистику контрагента"""
        try:
            counterparty = await db.get(Counterparty, counterparty_id)
            if not counterparty:
                return
            
            # Получаем статистику
            stats = await self._get_counterparty_stats(db, counterparty_id)
            
            # Обновляем
            counterparty.total_received = Decimal(str(stats["total_received"]))
            counterparty.total_paid = Decimal(str(stats["total_paid"]))
            counterparty.transaction_count = stats["transaction_count"]
            counterparty.updated_at = datetime.utcnow()
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error updating counterparty stats: {e}")
    
    # ==================== PRIVATE METHODS ====================
    
    async def _get_counterparty_stats(
        self,
        db: AsyncSession,
        counterparty_id: int
    ) -> Dict:
        """Получить статистику по контрагенту"""
        # Транзакции
        stmt = select(BankTransaction).where(
            BankTransaction.counterparty_id == counterparty_id
        )
        result = await db.execute(stmt)
        transactions = result.scalars().all()
        
        total_received = sum(
            tx.amount
            for tx in transactions
            if tx.category == "income"
        )
        
        total_paid = sum(
            tx.amount
            for tx in transactions
            if tx.category == "expense"
        )
        
        # Дебиторская задолженность
        ar_stmt = select(AccountsReceivable).where(
            AccountsReceivable.counterparty_id == counterparty_id
        )
        ar_result = await db.execute(ar_stmt)
        ar_list = ar_result.scalars().all()
        
        total_ar = sum(
            ar.amount - ar.paid_amount
            for ar in ar_list
            if ar.status != "paid"
        )
        
        return {
            "total_received": float(total_received),
            "total_paid": float(total_paid),
            "transaction_count": len(transactions),
            "total_ar": float(total_ar),
            "ar_count": len([ar for ar in ar_list if ar.status != "paid"])
        }
    
    def _format_counterparty(self, counterparty: Counterparty) -> Dict:
        """Форматировать контрагента для ответа"""
        return {
            "id": counterparty.id,
            "name": counterparty.name,
            "type": counterparty.type,
            "inn": counterparty.inn,
            "kpp": counterparty.kpp,
            "email": counterparty.email,
            "phone": counterparty.phone,
            "account_number": counterparty.account_number,
            "bank_name": counterparty.bank_name,
            "bic": counterparty.bic,
            "total_received": float(counterparty.total_received),
            "total_paid": float(counterparty.total_paid),
            "transaction_count": counterparty.transaction_count,
            "is_active": counterparty.is_active,
            "created_at": counterparty.created_at.isoformat()
        }


# Глобальный экземпляр
counterparty_service = CounterpartyService()


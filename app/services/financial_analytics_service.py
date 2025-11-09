"""
Сервис для расчета финансовых метрик и аналитики
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case
from sqlalchemy.orm import selectinload

from app.models import (
    BankAccount, BankTransaction, FinancialHealthMetrics,
    AccountsReceivable, User
)

logger = logging.getLogger(__name__)


class FinancialAnalyticsService:
    """Сервис для расчета финансовых метрик"""
    
    async def calculate_health_metrics(
        self,
        db: AsyncSession,
        user_id: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict:
        """
        Рассчитать метрики финансового здоровья за период
        
        Args:
            db: Database session
            user_id: ID пользователя
            period_start: Начало периода (по умолчанию - 30 дней назад)
            period_end: Конец периода (по умолчанию - сейчас)
        
        Returns:
            dict: Метрики финансового здоровья
        """
        try:
            if not period_end:
                period_end = datetime.utcnow()
            if not period_start:
                period_start = period_end - timedelta(days=30)
            
            # Получаем транзакции за период
            transactions = await self._get_transactions_in_period(
                db=db,
                user_id=user_id,
                period_start=period_start,
                period_end=period_end
            )
            
            # Получаем счета
            accounts = await self._get_user_accounts(db=db, user_id=user_id)
            
            # Получаем дебиторскую задолженность
            ar_data = await self._get_ar_data(db=db, user_id=user_id)
            
            # Рассчитываем метрики
            metrics = {
                # Доходы и расходы
                "total_revenue": self._calculate_revenue(transactions),
                "total_expenses": self._calculate_expenses(transactions),
                "net_income": Decimal(0),
                
                # Балансы
                "total_assets": self._calculate_total_assets(accounts),
                "total_liabilities": Decimal(0),  # Упрощенно, можно расширить
                "net_worth": Decimal(0),
                
                # Метрики ликвидности
                "current_ratio": None,
                "quick_ratio": None,
                
                # Дебиторская задолженность
                "total_ar": ar_data["total"],
                "overdue_ar": ar_data["overdue"],
                "ar_turnover_days": None,
                
                # Денежный поток
                "operating_cash_flow": Decimal(0),
                "cash_flow_trend": None,
                
                # Health score
                "health_score": None,
                "health_status": None
            }
            
            # Вычисляем производные метрики
            metrics["net_income"] = metrics["total_revenue"] - metrics["total_expenses"]
            metrics["net_worth"] = metrics["total_assets"] - metrics["total_liabilities"]
            metrics["operating_cash_flow"] = metrics["net_income"]
            
            # Коэффициенты ликвидности
            current_assets = metrics["total_assets"]
            current_liabilities = metrics["total_liabilities"] or Decimal(1)  # Избегаем деления на 0
            if current_liabilities > 0:
                metrics["current_ratio"] = current_assets / current_liabilities
            
            # Оборачиваемость ДЗ
            if metrics["total_revenue"] > 0:
                ar_turnover = metrics["total_ar"] / metrics["total_revenue"]
                days_in_period = (period_end - period_start).days
                metrics["ar_turnover_days"] = (ar_turnover * days_in_period) if days_in_period > 0 else None
            
            # Тренд денежного потока
            metrics["cash_flow_trend"] = self._calculate_cash_flow_trend(
                db=db,
                user_id=user_id,
                current_period_start=period_start,
                current_period_end=period_end
            )
            
            # Health score (0-100)
            metrics["health_score"] = self._calculate_health_score(metrics)
            metrics["health_status"] = self._get_health_status(metrics["health_score"])
            
            # Сохраняем метрики
            await self._save_metrics(
                db=db,
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                metrics=metrics
            )
            
            return {
                "success": True,
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat()
                },
                "metrics": self._format_metrics(metrics)
            }
            
        except Exception as e:
            logger.error(f"Error calculating health metrics: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """
        Получить сводку для дашборда
        
        Returns:
            dict: Сводка с основными метриками
        """
        try:
            # Текущий баланс
            accounts = await self._get_user_accounts(db=db, user_id=user_id)
            total_balance = sum(
                (acc.current_balance or Decimal(0)) 
                for acc in accounts 
                if acc.is_active
            )
            
            # Доходы и расходы за последние 30 дней
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=30)
            
            transactions = await self._get_transactions_in_period(
                db=db,
                user_id=user_id,
                period_start=period_start,
                period_end=period_end
            )
            
            revenue_30d = self._calculate_revenue(transactions)
            expenses_30d = self._calculate_expenses(transactions)
            
            # Дебиторская задолженность
            ar_data = await self._get_ar_data(db=db, user_id=user_id)
            
            # Последние метрики здоровья
            latest_metrics = await self._get_latest_metrics(db=db, user_id=user_id)
            
            return {
                "success": True,
                "summary": {
                    "total_balance": float(total_balance),
                    "revenue_30d": float(revenue_30d),
                    "expenses_30d": float(expenses_30d),
                    "net_income_30d": float(revenue_30d - expenses_30d),
                    "total_ar": float(ar_data["total"]),
                    "overdue_ar": float(ar_data["overdue"]),
                    "health_score": latest_metrics.get("health_score"),
                    "health_status": latest_metrics.get("health_status"),
                    "accounts_count": len([a for a in accounts if a.is_active])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==================== PRIVATE METHODS ====================
    
    async def _get_transactions_in_period(
        self,
        db: AsyncSession,
        user_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> List:
        """Получить транзакции за период"""
        stmt = select(BankTransaction).where(
            and_(
                BankTransaction.user_id == user_id,
                BankTransaction.booking_date >= period_start,
                BankTransaction.booking_date <= period_end
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _get_user_accounts(
        self,
        db: AsyncSession,
        user_id: int
    ) -> List:
        """Получить активные счета пользователя"""
        stmt = select(BankAccount).where(
            and_(
                BankAccount.user_id == user_id,
                BankAccount.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _get_ar_data(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """Получить данные по дебиторской задолженности"""
        stmt = select(AccountsReceivable).where(
            and_(
                AccountsReceivable.user_id == user_id,
                AccountsReceivable.status.in_(["pending", "partial", "overdue"])
            )
        )
        result = await db.execute(stmt)
        ar_list = result.scalars().all()
        
        total = sum(
            (ar.amount - ar.paid_amount) 
            for ar in ar_list
        )
        
        overdue = sum(
            (ar.amount - ar.paid_amount)
            for ar in ar_list
            if ar.status == "overdue" or (ar.due_date < datetime.utcnow() and ar.status != "paid")
        )
        
        return {
            "total": total,
            "overdue": overdue,
            "count": len(ar_list)
        }
    
    def _calculate_revenue(self, transactions: List) -> Decimal:
        """Рассчитать доходы"""
        return sum(
            tx.amount 
            for tx in transactions 
            if tx.category == "income" or tx.transaction_type == "credit"
        )
    
    def _calculate_expenses(self, transactions: List) -> Decimal:
        """Рассчитать расходы"""
        return sum(
            tx.amount 
            for tx in transactions 
            if tx.category == "expense" or tx.transaction_type == "debit"
        )
    
    def _calculate_total_assets(self, accounts: List) -> Decimal:
        """Рассчитать общие активы (балансы счетов)"""
        return sum(
            (acc.current_balance or Decimal(0))
            for acc in accounts
            if acc.is_active
        )
    
    def _calculate_cash_flow_trend(
        self,
        db: AsyncSession,
        user_id: int,
        current_period_start: datetime,
        current_period_end: datetime
    ) -> Optional[str]:
        """Рассчитать тренд денежного потока"""
        try:
            # Текущий период
            current_txs = await self._get_transactions_in_period(
                db=db,
                user_id=user_id,
                period_start=current_period_start,
                period_end=current_period_end
            )
            current_cf = self._calculate_revenue(current_txs) - self._calculate_expenses(current_txs)
            
            # Предыдущий период (такой же длины)
            period_length = current_period_end - current_period_start
            prev_period_end = current_period_start
            prev_period_start = prev_period_end - period_length
            
            prev_txs = await self._get_transactions_in_period(
                db=db,
                user_id=user_id,
                period_start=prev_period_start,
                period_end=prev_period_end
            )
            prev_cf = self._calculate_revenue(prev_txs) - self._calculate_expenses(prev_txs)
            
            if prev_cf == 0:
                return "stable"
            
            change_pct = ((current_cf - prev_cf) / abs(prev_cf)) * 100
            
            if change_pct > 10:
                return "increasing"
            elif change_pct < -10:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"Error calculating cash flow trend: {e}")
            return None
    
    def _calculate_health_score(self, metrics: Dict) -> int:
        """
        Рассчитать общий health score (0-100)
        
        Факторы:
        - Положительный денежный поток: 30 баллов
        - Низкая просроченная ДЗ: 25 баллов
        - Хорошая ликвидность: 25 баллов
        - Рост доходов: 20 баллов
        """
        score = 0
        
        # Денежный поток (0-30)
        if metrics["net_income"] > 0:
            score += 30
        elif metrics["net_income"] == 0:
            score += 15
        else:
            # Штраф за отрицательный поток
            score += max(0, 15 + int(metrics["net_income"] / metrics["total_revenue"] * 15) if metrics["total_revenue"] > 0 else 0)
        
        # Просроченная ДЗ (0-25)
        if metrics["total_ar"] > 0:
            overdue_ratio = metrics["overdue_ar"] / metrics["total_ar"]
            score += int((1 - overdue_ratio) * 25)
        else:
            score += 25  # Нет ДЗ - отлично
        
        # Ликвидность (0-25)
        if metrics["current_ratio"]:
            if metrics["current_ratio"] >= 2:
                score += 25
            elif metrics["current_ratio"] >= 1:
                score += 15
            else:
                score += max(0, int(metrics["current_ratio"] * 15))
        
        # Тренд денежного потока (0-20)
        if metrics["cash_flow_trend"] == "increasing":
            score += 20
        elif metrics["cash_flow_trend"] == "stable":
            score += 10
        else:
            score += 5
        
        return min(100, max(0, score))
    
    def _get_health_status(self, score: Optional[int]) -> str:
        """Определить статус здоровья по score"""
        if score is None:
            return "unknown"
        elif score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        elif score >= 20:
            return "poor"
        else:
            return "critical"
    
    def _format_metrics(self, metrics: Dict) -> Dict:
        """Форматировать метрики для ответа"""
        return {
            "revenue": {
                "total": float(metrics["total_revenue"]),
                "expenses": float(metrics["total_expenses"]),
                "net_income": float(metrics["net_income"])
            },
            "balance": {
                "total_assets": float(metrics["total_assets"]),
                "total_liabilities": float(metrics["total_liabilities"]),
                "net_worth": float(metrics["net_worth"])
            },
            "liquidity": {
                "current_ratio": float(metrics["current_ratio"]) if metrics["current_ratio"] else None,
                "quick_ratio": float(metrics["quick_ratio"]) if metrics["quick_ratio"] else None
            },
            "accounts_receivable": {
                "total": float(metrics["total_ar"]),
                "overdue": float(metrics["overdue_ar"]),
                "turnover_days": float(metrics["ar_turnover_days"]) if metrics["ar_turnover_days"] else None
            },
            "cash_flow": {
                "operating_cash_flow": float(metrics["operating_cash_flow"]),
                "trend": metrics["cash_flow_trend"]
            },
            "health": {
                "score": metrics["health_score"],
                "status": metrics["health_status"]
            }
        }
    
    async def _save_metrics(
        self,
        db: AsyncSession,
        user_id: int,
        period_start: datetime,
        period_end: datetime,
        metrics: Dict
    ):
        """Сохранить метрики в БД"""
        health_metrics = FinancialHealthMetrics(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            total_revenue=metrics["total_revenue"],
            total_expenses=metrics["total_expenses"],
            net_income=metrics["net_income"],
            total_assets=metrics["total_assets"],
            total_liabilities=metrics["total_liabilities"],
            net_worth=metrics["net_worth"],
            current_ratio=metrics["current_ratio"],
            quick_ratio=metrics["quick_ratio"],
            total_ar=metrics["total_ar"],
            overdue_ar=metrics["overdue_ar"],
            ar_turnover_days=metrics["ar_turnover_days"],
            operating_cash_flow=metrics["operating_cash_flow"],
            cash_flow_trend=metrics["cash_flow_trend"],
            health_score=metrics["health_score"],
            health_status=metrics["health_status"]
        )
        
        db.add(health_metrics)
        await db.commit()
        return health_metrics
    
    async def _get_latest_metrics(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """Получить последние метрики"""
        stmt = select(FinancialHealthMetrics).where(
            FinancialHealthMetrics.user_id == user_id
        ).order_by(FinancialHealthMetrics.calculated_at.desc()).limit(1)
        
        result = await db.execute(stmt)
        metrics = result.scalar_one_or_none()
        
        if metrics:
            return {
                "health_score": metrics.health_score,
                "health_status": metrics.health_status,
                "net_income": float(metrics.net_income) if metrics.net_income else 0
            }
        return {}


# Глобальный экземпляр
financial_analytics_service = FinancialAnalyticsService()


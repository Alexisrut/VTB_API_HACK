"""
Сервис для ML-прогнозирования денежных потоков
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import (
    BankTransaction, CashFlowPrediction, BankAccount,
    AccountsReceivable
)

logger = logging.getLogger(__name__)


class MLPredictionService:
    """
    Сервис для прогнозирования денежных потоков с использованием ML
    
    Для MVP используем упрощенные статистические модели:
    - Moving Average для базового прогноза
    - Seasonal decomposition для учета сезонности
    - Trend analysis для трендов
    """
    
    def __init__(self):
        self.model_version = "v1.0"
    
    async def predict_cash_flow(
        self,
        db: AsyncSession,
        user_id: int,
        weeks_ahead: int = 4,
        prediction_date: Optional[datetime] = None
    ) -> Dict:
        """
        Прогнозировать денежный поток на несколько недель вперед
        
        Args:
            db: Database session
            user_id: ID пользователя
            weeks_ahead: На сколько недель вперед прогнозировать (по умолчанию 4)
            prediction_date: Дата начала прогноза (по умолчанию - сейчас)
        
        Returns:
            dict: Прогнозы на каждую неделю
        """
        try:
            if not prediction_date:
                prediction_date = datetime.utcnow()
            
            # Получаем исторические данные (последние 6 месяцев)
            historical_data = await self._get_historical_cash_flow(
                db=db,
                user_id=user_id,
                months_back=6
            )
            
            if len(historical_data) < 4:  # Минимум 4 недели данных
                return {
                    "success": False,
                    "error": "Insufficient historical data for prediction"
                }
            
            # Получаем ожидаемые поступления (AR)
            expected_inflows = await self._get_expected_inflows(
                db=db,
                user_id=user_id,
                weeks_ahead=weeks_ahead,
                start_date=prediction_date
            )
            
            # Генерируем прогнозы
            predictions = []
            for week_num in range(1, weeks_ahead + 1):
                week_date = prediction_date + timedelta(weeks=week_num)
                
                # Прогнозируем приток
                predicted_inflow = self._predict_inflow(
                    historical_data=historical_data,
                    week_num=week_num,
                    expected_inflows=expected_inflows.get(week_num, Decimal(0))
                )
                
                # Прогнозируем отток
                predicted_outflow = self._predict_outflow(
                    historical_data=historical_data,
                    week_num=week_num
                )
                
                # Прогнозируем баланс
                current_balance = await self._get_current_balance(db=db, user_id=user_id)
                predicted_balance = current_balance + predicted_inflow - predicted_outflow
                
                # Рассчитываем вероятность кассового разрыва
                gap_probability, gap_amount = self._calculate_gap_probability(
                    predicted_balance=predicted_balance,
                    historical_data=historical_data
                )
                
                # Сохраняем прогноз
                prediction = CashFlowPrediction(
                    user_id=user_id,
                    prediction_date=week_date,
                    predicted_inflow=predicted_inflow,
                    predicted_outflow=predicted_outflow,
                    predicted_balance=predicted_balance,
                    gap_probability=gap_probability,
                    gap_amount=gap_amount,
                    model_version=self.model_version,
                    confidence_score=self._calculate_confidence(historical_data)
                )
                
                db.add(prediction)
                
                predictions.append({
                    "week": week_num,
                    "date": week_date.isoformat(),
                    "predicted_inflow": float(predicted_inflow),
                    "predicted_outflow": float(predicted_outflow),
                    "predicted_balance": float(predicted_balance),
                    "gap_probability": float(gap_probability) if gap_probability else None,
                    "gap_amount": float(gap_amount) if gap_amount else None,
                    "confidence_score": float(prediction.confidence_score) if prediction.confidence_score else None
                })
            
            await db.commit()
            
            return {
                "success": True,
                "predictions": predictions,
                "model_version": self.model_version,
                "current_balance": float(current_balance)
            }
            
        except Exception as e:
            logger.error(f"Error predicting cash flow: {e}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_cash_flow_gaps(
        self,
        db: AsyncSession,
        user_id: int,
        weeks_ahead: int = 4
    ) -> Dict:
        """
        Получить прогноз кассовых разрывов
        
        Returns:
            dict: Список потенциальных разрывов
        """
        try:
            # Получаем прогнозы
            prediction_result = await self.predict_cash_flow(
                db=db,
                user_id=user_id,
                weeks_ahead=weeks_ahead
            )
            
            if not prediction_result.get("success"):
                return prediction_result
            
            predictions = prediction_result.get("predictions", [])
            
            # Фильтруем только те, где есть риск разрыва
            gaps = []
            for pred in predictions:
                if pred.get("gap_probability", 0) > 30:  # Вероятность > 30%
                    gaps.append({
                        "date": pred["date"],
                        "week": pred["week"],
                        "predicted_balance": pred["predicted_balance"],
                        "gap_probability": pred["gap_probability"],
                        "gap_amount": pred.get("gap_amount", 0),
                        "predicted_inflow": pred["predicted_inflow"],
                        "predicted_outflow": pred["predicted_outflow"]
                    })
            
            return {
                "success": True,
                "gaps": gaps,
                "total_gaps": len(gaps)
            }
            
        except Exception as e:
            logger.error(f"Error getting cash flow gaps: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==================== PRIVATE METHODS ====================
    
    async def _get_historical_cash_flow(
        self,
        db: AsyncSession,
        user_id: int,
        months_back: int = 6
    ) -> List[Dict]:
        """
        Получить исторические данные о денежных потоках по неделям
        
        Returns:
            list: Список словарей с недельными данными
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months_back * 30)
        
        # Получаем транзакции
        stmt = select(BankTransaction).where(
            and_(
                BankTransaction.user_id == user_id,
                BankTransaction.booking_date >= start_date,
                BankTransaction.booking_date <= end_date
            )
        ).order_by(BankTransaction.booking_date)
        
        result = await db.execute(stmt)
        transactions = result.scalars().all()
        
        # Группируем по неделям
        weekly_data = {}
        for tx in transactions:
            # Определяем неделю
            week_start = tx.booking_date - timedelta(days=tx.booking_date.weekday())
            week_key = week_start.strftime("%Y-%W")
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "week_start": week_start,
                    "inflow": Decimal(0),
                    "outflow": Decimal(0)
                }
            
            if tx.category == "income" or tx.transaction_type == "credit":
                weekly_data[week_key]["inflow"] += tx.amount
            else:
                weekly_data[week_key]["outflow"] += tx.amount
        
        # Преобразуем в список и сортируем
        historical = sorted(
            weekly_data.values(),
            key=lambda x: x["week_start"]
        )
        
        return historical
    
    async def _get_expected_inflows(
        self,
        db: AsyncSession,
        user_id: int,
        weeks_ahead: int,
        start_date: datetime
    ) -> Dict[int, Decimal]:
        """
        Получить ожидаемые поступления из дебиторской задолженности
        
        Returns:
            dict: {week_num: amount}
        """
        end_date = start_date + timedelta(weeks=weeks_ahead)
        
        stmt = select(AccountsReceivable).where(
            and_(
                AccountsReceivable.user_id == user_id,
                AccountsReceivable.status.in_(["pending", "partial"]),
                AccountsReceivable.due_date >= start_date,
                AccountsReceivable.due_date <= end_date
            )
        )
        
        result = await db.execute(stmt)
        ar_list = result.scalars().all()
        
        expected = {}
        for ar in ar_list:
            # Определяем неделю
            days_diff = (ar.due_date - start_date).days
            week_num = (days_diff // 7) + 1
            
            if week_num <= weeks_ahead:
                amount = ar.amount - ar.paid_amount
                if week_num not in expected:
                    expected[week_num] = Decimal(0)
                expected[week_num] += amount
        
        return expected
    
    def _predict_inflow(
        self,
        historical_data: List[Dict],
        week_num: int,
        expected_inflows: Decimal = Decimal(0)
    ) -> Decimal:
        """
        Прогнозировать приток денежных средств
        
        Использует:
        - Moving Average для базового прогноза
        - Ожидаемые поступления из AR
        """
        if len(historical_data) == 0:
            return Decimal(0)
        
        # Берем последние 4 недели для MA
        recent_weeks = historical_data[-4:] if len(historical_data) >= 4 else historical_data
        
        # Простое скользящее среднее
        avg_inflow = sum(w["inflow"] for w in recent_weeks) / len(recent_weeks)
        
        # Учитываем тренд
        if len(historical_data) >= 2:
            recent_trend = (recent_weeks[-1]["inflow"] - recent_weeks[0]["inflow"]) / len(recent_weeks)
            trend_adjustment = recent_trend * week_num * Decimal("0.3")  # Смягчаем тренд
        else:
            trend_adjustment = Decimal(0)
        
        predicted = avg_inflow + trend_adjustment + expected_inflows
        
        return max(Decimal(0), predicted)
    
    def _predict_outflow(
        self,
        historical_data: List[Dict],
        week_num: int
    ) -> Decimal:
        """
        Прогнозировать отток денежных средств
        
        Использует Moving Average с учетом тренда
        """
        if len(historical_data) == 0:
            return Decimal(0)
        
        # Берем последние 4 недели для MA
        recent_weeks = historical_data[-4:] if len(historical_data) >= 4 else historical_data
        
        # Простое скользящее среднее
        avg_outflow = sum(w["outflow"] for w in recent_weeks) / len(recent_weeks)
        
        # Учитываем тренд
        if len(historical_data) >= 2:
            recent_trend = (recent_weeks[-1]["outflow"] - recent_weeks[0]["outflow"]) / len(recent_weeks)
            trend_adjustment = recent_trend * week_num * Decimal("0.3")
        else:
            trend_adjustment = Decimal(0)
        
        predicted = avg_outflow + trend_adjustment
        
        return max(Decimal(0), predicted)
    
    def _calculate_gap_probability(
        self,
        predicted_balance: Decimal,
        historical_data: List[Dict]
    ) -> tuple:
        """
        Рассчитать вероятность кассового разрыва
        
        Returns:
            tuple: (probability %, gap_amount)
        """
        if predicted_balance >= 0:
            return None, None
        
        # Рассчитываем вероятность на основе исторической волатильности
        if len(historical_data) < 2:
            return Decimal(50), abs(predicted_balance)
        
        # Вычисляем стандартное отклонение балансов
        balances = []
        running_balance = Decimal(0)
        for week in historical_data:
            running_balance += week["inflow"] - week["outflow"]
            balances.append(float(running_balance))
        
        if len(balances) < 2:
            return Decimal(50), abs(predicted_balance)
        
        std_dev = np.std(balances)
        mean_balance = np.mean(balances)
        
        # Если прогнозируемый баланс отрицательный
        gap_amount = abs(predicted_balance)
        
        # Вероятность зависит от того, насколько далеко от среднего
        if std_dev > 0:
            z_score = abs((float(predicted_balance) - mean_balance) / std_dev)
            # Преобразуем z-score в вероятность (упрощенно)
            probability = min(100, max(10, 50 + int(z_score * 15)))
        else:
            probability = 50 if predicted_balance < 0 else 0
        
        return Decimal(probability), gap_amount
    
    def _calculate_confidence(self, historical_data: List[Dict]) -> Decimal:
        """
        Рассчитать уверенность модели (0-100)
        
        Зависит от количества исторических данных
        """
        if len(historical_data) >= 12:  # 3 месяца
            return Decimal(85)
        elif len(historical_data) >= 8:  # 2 месяца
            return Decimal(70)
        elif len(historical_data) >= 4:  # 1 месяц
            return Decimal(55)
        else:
            return Decimal(40)
    
    async def _get_current_balance(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Decimal:
        """Получить текущий баланс всех счетов"""
        stmt = select(BankAccount).where(
            and_(
                BankAccount.user_id == user_id,
                BankAccount.is_active == True
            )
        )
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        
        total = sum(
            (acc.current_balance or Decimal(0))
            for acc in accounts
        )
        
        return total


# Глобальный экземпляр
ml_prediction_service = MLPredictionService()


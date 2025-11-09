"""
Роутер для ML-прогнозов денежных потоков
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.ml_prediction_service import ml_prediction_service

router = APIRouter(prefix="/api/v1/predictions", tags=["Cash Flow Predictions"])


@router.get("/cash-flow")
async def predict_cash_flow(
    weeks_ahead: int = Query(4, ge=1, le=12, description="На сколько недель вперед прогнозировать"),
    prediction_date: Optional[str] = Query(None, description="Дата начала прогноза (YYYY-MM-DD)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Прогнозировать денежный поток на несколько недель вперед
    
    **Параметры:**
    - **weeks_ahead**: На сколько недель вперед прогнозировать (1-12, по умолчанию 4)
    - **prediction_date**: Дата начала прогноза (по умолчанию - сейчас)
    
    **Возвращает:**
    - Прогнозы на каждую неделю с вероятностью кассовых разрывов
    """
    try:
        prediction_date_dt = None
        if prediction_date:
            prediction_date_dt = datetime.fromisoformat(prediction_date)
        
        result = await ml_prediction_service.predict_cash_flow(
            db=db,
            user_id=user_id,
            weeks_ahead=weeks_ahead,
            prediction_date=prediction_date_dt
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to generate prediction")
            )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/cash-flow-gaps")
async def get_cash_flow_gaps(
    weeks_ahead: int = Query(4, ge=1, le=12, description="На сколько недель вперед проверять"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить прогноз кассовых разрывов
    
    **Параметры:**
    - **weeks_ahead**: На сколько недель вперед проверять (1-12, по умолчанию 4)
    
    **Возвращает:**
    - Список потенциальных кассовых разрывов с вероятностью и размером
    """
    try:
        result = await ml_prediction_service.get_cash_flow_gaps(
            db=db,
            user_id=user_id,
            weeks_ahead=weeks_ahead
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to get cash flow gaps")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


"""
Роутер для финансовой аналитики
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.security.oauth2 import get_current_user
from app.services.financial_analytics_service import financial_analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Financial Analytics"])


@router.get("/health-metrics")
async def get_health_metrics(
    period_start: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    period_end: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить метрики финансового здоровья за период
    
    **Параметры:**
    - **period_start**: Начало периода (по умолчанию - 30 дней назад)
    - **period_end**: Конец периода (по умолчанию - сейчас)
    
    **Возвращает:**
    - Метрики финансового здоровья
    """
    try:
        period_start_dt = None
        period_end_dt = None
        
        if period_start:
            period_start_dt = datetime.fromisoformat(period_start)
        if period_end:
            period_end_dt = datetime.fromisoformat(period_end)
        
        result = await financial_analytics_service.calculate_health_metrics(
            db=db,
            user_id=user_id,
            period_start=period_start_dt,
            period_end=period_end_dt
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to calculate metrics")
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


@router.get("/dashboard")
async def get_dashboard_summary(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить сводку для дашборда
    
    **Возвращает:**
    - Основные метрики для отображения на дашборде
    """
    try:
        result = await financial_analytics_service.get_dashboard_summary(
            db=db,
            user_id=user_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to get dashboard summary")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


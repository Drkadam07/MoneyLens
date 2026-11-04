from datetime import date
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.analytics.schemas import (
    CoverageResponse,
    DailySpendingPoint,
    FinancialSummaryResponse,
    MonthlySpendingPoint,
)
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=FinancialSummaryResponse)
async def get_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    service = AnalyticsService(db, current_user.id)
    return await service.get_summary(start_date, end_date)


@router.get("/categories")
async def get_categories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    service = AnalyticsService(db, current_user.id)
    return await service.get_categories(start_date, end_date)


@router.get("/daily", response_model=List[DailySpendingPoint])
async def get_daily_series(
    start_date: date,
    end_date: date,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AnalyticsService(db, current_user.id)
    return await service.get_daily_series(start_date, end_date)


@router.get("/monthly", response_model=List[MonthlySpendingPoint])
async def get_monthly_series(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AnalyticsService(db, current_user.id)
    return await service.get_monthly_series()


@router.get("/coverage", response_model=CoverageResponse)
async def get_coverage(
    start_date: date,
    end_date: date,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AnalyticsService(db, current_user.id)
    return await service.get_coverage(start_date, end_date)

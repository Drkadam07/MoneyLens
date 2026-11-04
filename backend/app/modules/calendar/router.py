from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.calendar.schemas import FinancialCalendarResponse
from app.modules.calendar.service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("", response_model=FinancialCalendarResponse)
async def get_calendar(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    year: int = Query(default_factory=lambda: datetime.now(timezone.utc).year),
    month: int = Query(default_factory=lambda: datetime.now(timezone.utc).month, ge=1, le=12),
):
    service = CalendarService(db, current_user.id)
    return await service.get_monthly_calendar(year, month)

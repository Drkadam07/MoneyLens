import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.recurring.schemas import RecurringConfirmRequest, RecurringPaymentResponse
from app.modules.recurring.service import RecurringPaymentService

router = APIRouter(prefix="/recurring", tags=["Recurring Payments"])


@router.get("", response_model=List[RecurringPaymentResponse])
async def list_recurring(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = RecurringPaymentService(db, current_user.id)
    return await service.list_recurring()


@router.post("/{item_id}/confirm", response_model=RecurringPaymentResponse)
async def confirm_recurring(
    item_id: uuid.UUID,
    data: RecurringConfirmRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = RecurringPaymentService(db, current_user.id)
    return await service.confirm_recurring(item_id, data.user_confirmed)

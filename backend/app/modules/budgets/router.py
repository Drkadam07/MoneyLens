import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.budgets.schemas import BudgetCreate, BudgetProgressResponse
from app.modules.budgets.service import BudgetService

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("", response_model=List[BudgetProgressResponse])
async def list_budgets(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BudgetService(db, current_user.id)
    return await service.list_budgets()


@router.post("", response_model=BudgetProgressResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BudgetService(db, current_user.id)
    return await service.create_budget(data)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BudgetService(db, current_user.id)
    await service.delete_budget(budget_id)
    return None

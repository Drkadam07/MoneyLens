import uuid
from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.transactions.schemas import (
    CategoryUpdate,
    NoteCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.modules.transactions.service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    payment_method: Optional[str] = Query(None),
    transaction_kind: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    service = TransactionService(db, current_user.id)
    return await service.list_transactions(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        category_id=category_id,
        payment_method=payment_method,
        transaction_kind=transaction_kind,
        search_query=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{tx_id}", response_model=TransactionResponse)
async def get_transaction(
    tx_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = TransactionService(db, current_user.id)
    return await service.get_transaction(tx_id)


@router.patch("/{tx_id}", response_model=TransactionResponse)
async def update_transaction(
    tx_id: uuid.UUID,
    data: TransactionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = TransactionService(db, current_user.id)
    return await service.update_transaction(tx_id, data)


@router.patch("/{tx_id}/category", response_model=TransactionResponse)
async def update_transaction_category(
    tx_id: uuid.UUID,
    data: CategoryUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = TransactionService(db, current_user.id)
    return await service.update_transaction(tx_id, TransactionUpdate(category_id=data.category_id))


@router.post("/{tx_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_transaction_note(
    tx_id: uuid.UUID,
    data: NoteCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = TransactionService(db, current_user.id)
    await service.add_note(tx_id, data.note)
    return {"message": "Note added successfully"}

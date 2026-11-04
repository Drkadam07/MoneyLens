import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.accounts.schemas import BankAccountCreate, BankAccountResponse, BankAccountUpdate
from app.modules.accounts.service import BankAccountService

router = APIRouter(prefix="/accounts", tags=["Bank Accounts"])


@router.get("", response_model=List[BankAccountResponse])
async def list_accounts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BankAccountService(db, current_user.id)
    return await service.list_accounts()


@router.post("", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: BankAccountCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BankAccountService(db, current_user.id)
    return await service.create_account(data)


@router.get("/{account_id}", response_model=BankAccountResponse)
async def get_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BankAccountService(db, current_user.id)
    return await service.get_account(account_id)


@router.patch("/{account_id}", response_model=BankAccountResponse)
async def update_account(
    account_id: uuid.UUID,
    data: BankAccountUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BankAccountService(db, current_user.id)
    return await service.update_account(account_id, data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = BankAccountService(db, current_user.id)
    await service.delete_account(account_id)
    return None

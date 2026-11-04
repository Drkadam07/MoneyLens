import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.models.account import BankAccount
from app.modules.accounts.schemas import BankAccountCreate, BankAccountResponse, BankAccountUpdate


class BankAccountService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_accounts(self) -> List[BankAccountResponse]:
        result = await self.db.execute(
            select(BankAccount)
            .where(BankAccount.user_id == self.user_id)
            .order_by(BankAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        return [BankAccountResponse.model_validate(acc) for acc in accounts]

    async def create_account(self, data: BankAccountCreate) -> BankAccountResponse:
        account = BankAccount(
            user_id=self.user_id,
            bank_name=data.bank_name,
            account_label=data.account_label,
            account_type=data.account_type,
            masked_account_number=data.masked_account_number,
            currency=data.currency,
            is_active=True,
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return BankAccountResponse.model_validate(account)

    async def get_account(self, account_id: uuid.UUID) -> BankAccountResponse:
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.user_id == self.user_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError(f"Bank account '{account_id}' not found")
        return BankAccountResponse.model_validate(account)

    async def update_account(self, account_id: uuid.UUID, data: BankAccountUpdate) -> BankAccountResponse:
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.user_id == self.user_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError(f"Bank account '{account_id}' not found")

        if data.account_label is not None:
            account.account_label = data.account_label
        if data.account_type is not None:
            account.account_type = data.account_type
        if data.is_active is not None:
            account.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(account)
        return BankAccountResponse.model_validate(account)

    async def delete_account(self, account_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.user_id == self.user_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError(f"Bank account '{account_id}' not found")

        await self.db.delete(account)
        await self.db.commit()

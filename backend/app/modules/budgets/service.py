import uuid
from decimal import Decimal
from typing import List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.database.models.planning import Budget
from app.database.models.transaction import Category, Transaction, TransactionKind
from app.modules.budgets.schemas import BudgetCreate, BudgetProgressResponse, BudgetUpdate


class BudgetService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_budgets(self) -> List[BudgetProgressResponse]:
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(Budget.user_id == self.user_id)
            .order_by(Budget.created_at.desc())
        )
        res = await self.db.execute(stmt)
        budgets = res.scalars().all()

        results = []
        for b in budgets:
            # Query actual spent in budget's date range
            spent_query = select(func.sum(Transaction.debit_amount)).where(
                Transaction.user_id == self.user_id,
                Transaction.category_id == b.category_id,
                Transaction.transaction_kind == TransactionKind.EXPENSE,
                Transaction.transaction_date >= b.start_date,
                Transaction.transaction_date <= b.end_date,
            )
            spent_res = await self.db.execute(spent_query)
            spent = spent_res.scalar() or Decimal("0.00")

            remaining = b.amount - spent
            pct = float((spent / b.amount) * 100.0) if b.amount > Decimal("0.00") else 0.0

            results.append(
                BudgetProgressResponse(
                    id=b.id,
                    category_id=b.category_id,
                    category_name=b.category.name if b.category else "Uncategorized",
                    amount_budgeted=b.amount,
                    amount_spent=spent,
                    amount_remaining=remaining,
                    percentage_used=round(pct, 2),
                    start_date=b.start_date,
                    end_date=b.end_date,
                    is_overbudget=spent > b.amount,
                )
            )
        return results

    async def create_budget(self, data: BudgetCreate) -> BudgetProgressResponse:
        budget = Budget(
            user_id=self.user_id,
            category_id=data.category_id,
            amount=data.amount,
            period_type=data.period_type,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        budgets = await self.list_budgets()
        return next(b for b in budgets if b.id == budget.id)

    async def delete_budget(self, budget_id: uuid.UUID) -> None:
        stmt = select(Budget).where(Budget.id == budget_id, Budget.user_id == self.user_id)
        res = await self.db.execute(stmt)
        b = res.scalar_one_or_none()
        if not b:
            raise NotFoundError(f"Budget '{budget_id}' not found")
        await self.db.delete(b)
        await self.db.commit()

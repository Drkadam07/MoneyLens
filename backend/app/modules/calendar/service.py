import calendar
import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.statement import Statement, StatementStatus
from app.database.models.transaction import Transaction, TransactionKind
from app.modules.calendar.schemas import (
    CalendarDaySummary,
    CalendarTransactionItem,
    FinancialCalendarResponse,
)


class CalendarService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def get_monthly_calendar(self, year: int, month: int) -> FinancialCalendarResponse:
        _, num_days = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        # 1. Fetch statements overlapping with this month
        stmt_res = await self.db.execute(
            select(Statement).where(
                Statement.user_id == self.user_id,
                Statement.status.in_([StatementStatus.CONFIRMED, StatementStatus.ANALYZED]),
                Statement.period_start <= end_date,
                Statement.period_end >= start_date,
            )
        )
        statements = stmt_res.scalars().all()

        covered_days = set()
        for s in statements:
            p_start = max(s.period_start, start_date) if s.period_start else start_date
            p_end = min(s.period_end, end_date) if s.period_end else end_date
            for d in range((p_end - p_start).days + 1):
                from datetime import timedelta
                covered_days.add(p_start + timedelta(days=d))

        # 2. Fetch transactions for this month
        tx_res = await self.db.execute(
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                Transaction.user_id == self.user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .order_by(Transaction.transaction_date.asc())
        )
        transactions = tx_res.scalars().all()

        # Group transactions by day
        tx_by_day: Dict[date, List[Transaction]] = {}
        for tx in transactions:
            tx_by_day.setdefault(tx.transaction_date, []).append(tx)

        day_summaries = []
        total_monthly_expense = Decimal("0.00")
        total_monthly_income = Decimal("0.00")
        highest_spending_day = None
        max_daily_expense = Decimal("0.00")

        for d in range(1, num_days + 1):
            curr_date = date(year, month, d)
            has_cov = curr_date in covered_days
            day_txs = tx_by_day.get(curr_date, [])

            day_expense = Decimal("0.00")
            day_income = Decimal("0.00")
            tx_items = []

            for tx in day_txs:
                if tx.transaction_kind == TransactionKind.EXPENSE:
                    day_expense += tx.debit_amount
                    amt = tx.debit_amount
                elif tx.transaction_kind == TransactionKind.INCOME:
                    day_income += tx.credit_amount
                    amt = tx.credit_amount
                else:
                    amt = tx.debit_amount if tx.debit_amount > 0 else tx.credit_amount

                tx_items.append(
                    CalendarTransactionItem(
                        id=str(tx.id),
                        description=tx.description_normalized,
                        amount=amt,
                        kind=tx.transaction_kind.value,
                        category=tx.category.name if tx.category else None,
                    )
                )

            total_monthly_expense += day_expense
            total_monthly_income += day_income

            if day_expense > max_daily_expense:
                max_daily_expense = day_expense
                highest_spending_day = str(curr_date)

            # Intensity: 0 to 4 based on spend amount
            if day_expense == Decimal("0.00"):
                intensity = 0
            elif day_expense < Decimal("500.00"):
                intensity = 1
            elif day_expense < Decimal("2000.00"):
                intensity = 2
            elif day_expense < Decimal("5000.00"):
                intensity = 3
            else:
                intensity = 4

            day_summaries.append(
                CalendarDaySummary(
                    date=str(curr_date),
                    day=d,
                    has_coverage=has_cov,
                    total_expense=day_expense,
                    total_income=day_income,
                    net_cash_flow=day_income - day_expense,
                    transaction_count=len(day_txs),
                    spending_intensity=intensity,
                    transactions=tx_items,
                )
            )

        month_name = calendar.month_name[month]

        return FinancialCalendarResponse(
            year=year,
            month=month,
            month_name=month_name,
            total_monthly_expense=total_monthly_expense,
            total_monthly_income=total_monthly_income,
            highest_spending_day=highest_spending_day,
            days=day_summaries,
        )

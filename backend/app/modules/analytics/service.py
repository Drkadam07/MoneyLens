import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.transaction import Transaction, TransactionKind
from app.financial.calculations import FinancialCalculationService
from app.financial.coverage import CoverageService
from app.modules.analytics.schemas import (
    DailySpendingPoint,
    FinancialSummaryResponse,
    MonthlySpendingPoint,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.calc_service = FinancialCalculationService(db, user_id)
        self.coverage_service = CoverageService(db, user_id)

    async def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> FinancialSummaryResponse:
        data = await self.calc_service.get_financial_summary(start_date, end_date)
        return FinancialSummaryResponse(**data)

    async def get_categories(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        return await self.calc_service.get_category_breakdown(start_date, end_date)

    async def get_daily_series(
        self, start_date: date, end_date: date
    ) -> List[DailySpendingPoint]:
        query = (
            select(
                Transaction.transaction_date,
                func.sum(
                    func.case(
                        (Transaction.transaction_kind == TransactionKind.INCOME, Transaction.credit_amount),
                        else_=0,
                    )
                ).label("income"),
                func.sum(
                    func.case(
                        (Transaction.transaction_kind == TransactionKind.EXPENSE, Transaction.debit_amount),
                        else_=0,
                    )
                ).label("expense"),
                func.count(Transaction.id).label("count"),
            )
            .where(
                Transaction.user_id == self.user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date.asc())
        )
        res = await self.db.execute(query)
        rows = res.all()

        points = []
        for r in rows:
            inc = Decimal(str(r.income or 0))
            exp = Decimal(str(r.expense or 0))
            points.append(
                DailySpendingPoint(
                    date=str(r.transaction_date),
                    income=inc,
                    expense=exp,
                    net=inc - exp,
                    count=r.count,
                )
            )
        return points

    async def get_monthly_series(self) -> List[MonthlySpendingPoint]:
        # Group by year-month
        query = (
            select(
                func.to_char(Transaction.transaction_date, "YYYY-MM").label("month"),
                func.sum(
                    func.case(
                        (Transaction.transaction_kind == TransactionKind.INCOME, Transaction.credit_amount),
                        else_=0,
                    )
                ).label("income"),
                func.sum(
                    func.case(
                        (Transaction.transaction_kind == TransactionKind.EXPENSE, Transaction.debit_amount),
                        else_=0,
                    )
                ).label("expense"),
                func.count(Transaction.id).label("count"),
            )
            .where(Transaction.user_id == self.user_id)
            .group_by("month")
            .order_by("month")
        )
        res = await self.db.execute(query)
        rows = res.all()

        points = []
        for r in rows:
            inc = Decimal(str(r.income or 0))
            exp = Decimal(str(r.expense or 0))
            points.append(
                MonthlySpendingPoint(
                    month=r.month,
                    income=inc,
                    expense=exp,
                    net=inc - exp,
                    count=r.count,
                )
            )
        return points

    async def get_coverage(self, start_date: date, end_date: date):
        return await self.coverage_service.get_coverage_report(start_date, end_date)

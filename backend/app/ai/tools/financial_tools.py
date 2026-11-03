import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.planning import RecurringPayment
from app.database.models.transaction import Category, Transaction, TransactionKind
from app.financial.calculations import FinancialCalculationService


class FinancialToolBelt:
    """Authorized, deterministic, read-only financial data tools for AI Agents.
    
    CRITICAL SECURITY & RELIABILITY RULE:
    - Never accept user_id from LLM arguments; it is passed from the server authentication context.
    - All monetary aggregations are calculated via pure SQL and Decimal.
    """

    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.calc_service = FinancialCalculationService(db, user_id)

    async def get_financial_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Compute exact income, expense, and net cash flow for a date range."""
        summary = await self.calc_service.get_financial_summary(start_date, end_date)
        # Convert Decimals to string/float for JSON serialization
        return {
            k: (str(v) if isinstance(v, Decimal) else v)
            for k, v in summary.items()
        }

    async def get_category_breakdown(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Return spending breakdown by category with amounts, percentages, and transaction counts."""
        items = await self.calc_service.get_category_breakdown(start_date, end_date)
        return [
            {
                "category": i["category"],
                "amount": str(i["amount"]),
                "count": i["count"],
                "percentage": i["percentage"],
            }
            for i in items
        ]

    async def search_transactions(
        self,
        query: Optional[str] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search transactions by merchant, narration, or amount boundaries."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category),
                selectinload(Transaction.merchant),
            )
            .where(Transaction.user_id == self.user_id)
        )

        if start_date:
            stmt = stmt.where(Transaction.transaction_date >= start_date)
        if end_date:
            stmt = stmt.where(Transaction.transaction_date <= end_date)
        if min_amount is not None:
            stmt = stmt.where(
                (Transaction.debit_amount >= min_amount) | (Transaction.credit_amount >= min_amount)
            )
        if max_amount is not None:
            stmt = stmt.where(
                (Transaction.debit_amount <= max_amount) & (Transaction.credit_amount <= max_amount)
            )
        if query:
            pat = f"%{query.strip()}%"
            stmt = stmt.where(
                Transaction.description_normalized.ilike(pat)
                | Transaction.description_original.ilike(pat)
            )

        stmt = stmt.order_by(Transaction.transaction_date.desc()).limit(limit)
        res = await self.db.execute(stmt)
        txs = res.scalars().all()

        return [
            {
                "id": str(t.id),
                "date": str(t.transaction_date),
                "description": t.description_normalized,
                "debit": str(t.debit_amount),
                "credit": str(t.credit_amount),
                "category": t.category.name if t.category else "Uncategorized",
                "merchant": t.merchant.display_name if t.merchant else None,
                "payment_method": t.payment_method.value,
            }
            for t in txs
        ]

    async def compare_periods(
        self,
        start_a: date,
        end_a: date,
        start_b: date,
        end_b: date,
    ) -> Dict[str, Any]:
        """Compare financial performance and spending between two distinct periods."""
        summary_a = await self.calc_service.get_financial_summary(start_a, end_a)
        summary_b = await self.calc_service.get_financial_summary(start_b, end_b)

        exp_a = summary_a["expenses"]
        exp_b = summary_b["expenses"]
        diff = exp_b - exp_a
        pct_change = float((diff / exp_a) * 100.0) if exp_a > Decimal("0.00") else 0.0

        return {
            "period_a": {
                "start": str(start_a),
                "end": str(end_a),
                "expenses": str(exp_a),
                "income": str(summary_a["income"]),
                "net_cash_flow": str(summary_a["net_cash_flow"]),
            },
            "period_b": {
                "start": str(start_b),
                "end": str(end_b),
                "expenses": str(exp_b),
                "income": str(summary_b["income"]),
                "net_cash_flow": str(summary_b["net_cash_flow"]),
            },
            "expense_difference": str(diff),
            "percentage_change": round(pct_change, 2),
            "direction": "INCREASED" if diff > 0 else ("DECREASED" if diff < 0 else "UNCHANGED"),
        }

    async def get_recurring_payments(self) -> List[Dict[str, Any]]:
        """Retrieve confirmed and detected recurring subscriptions and bills."""
        stmt = (
            select(RecurringPayment)
            .where(
                RecurringPayment.user_id == self.user_id,
                RecurringPayment.status == "ACTIVE",
            )
            .order_by(RecurringPayment.expected_amount.desc())
        )
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        return [
            {
                "id": str(i.id),
                "title": i.title,
                "amount": str(i.expected_amount),
                "frequency": i.frequency,
                "next_expected_date": str(i.next_expected_date),
            }
            for i in items
        ]

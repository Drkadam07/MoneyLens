from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.transaction import Transaction, TransactionKind


class FinancialCalculationService:
    """Core deterministic financial intelligence service.
    
    CRITICAL PRINCIPLE:
    - Never uses floating-point arithmetic.
    - Debit != Expense (transfers, investments, withdrawals excluded).
    - Credit != Income (refunds, transfers excluded).
    - Net Cash Flow = Classified Income - Classified Expenses.
    """

    def __init__(self, db: Optional[AsyncSession], user_id):
        self.db = db
        self.user_id = user_id

    @staticmethod
    def calculate_summary_from_transactions(
        transactions: List[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Pure deterministic financial calculation on a set of transactions."""
        classified_income = Decimal("0.00")
        classified_expenses = Decimal("0.00")
        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")
        transfers_excluded = Decimal("0.00")
        refunds_total = Decimal("0.00")
        investments_total = Decimal("0.00")
        unclassified_amount = Decimal("0.00")

        transaction_count = len(transactions)
        expense_counts = 0
        max_expense = Decimal("0.00")

        for tx in transactions:
            total_debits += tx.debit_amount
            total_credits += tx.credit_amount

            if tx.transaction_kind == TransactionKind.INCOME:
                classified_income += tx.credit_amount
            elif tx.transaction_kind == TransactionKind.EXPENSE:
                classified_expenses += tx.debit_amount
                expense_counts += 1
                if tx.debit_amount > max_expense:
                    max_expense = tx.debit_amount
            elif tx.transaction_kind == TransactionKind.TRANSFER:
                transfers_excluded += (tx.debit_amount + tx.credit_amount)
            elif tx.transaction_kind == TransactionKind.REFUND:
                refunds_total += tx.credit_amount
            elif tx.transaction_kind == TransactionKind.INVESTMENT:
                investments_total += tx.debit_amount
            elif tx.transaction_kind == TransactionKind.UNCLASSIFIED:
                unclassified_amount += (tx.debit_amount + tx.credit_amount)

        net_cash_flow = classified_income - classified_expenses
        avg_expense = (classified_expenses / expense_counts) if expense_counts > 0 else Decimal("0.00")
        savings_rate = (
            ((net_cash_flow / classified_income) * Decimal("100.00"))
            if classified_income > Decimal("0.00")
            else Decimal("0.00")
        )

        return {
            "period": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            },
            "currency": "INR",
            "income": classified_income,
            "expenses": classified_expenses,
            "net_cash_flow": net_cash_flow,
            "savings_rate_pct": float(round(savings_rate, 2)),
            "total_debits": total_debits,
            "total_credits": total_credits,
            "transfers_excluded": transfers_excluded,
            "refunds_total": refunds_total,
            "investments_total": investments_total,
            "unclassified_amount": unclassified_amount,
            "transaction_count": transaction_count,
            "average_expense": avg_expense,
            "highest_expense": max_expense,
        }

    async def get_financial_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Compute authoritative income, expense, and net cash flow for a date range from DB."""
        if not self.db:
            raise RuntimeError("Database session required for query execution")

        query = select(Transaction).where(Transaction.user_id == self.user_id)

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)
        if account_id:
            query = query.where(Transaction.account_id == account_id)

        res = await self.db.execute(query)
        transactions = res.scalars().all()
        return self.calculate_summary_from_transactions(transactions, start_date, end_date)

    async def get_category_breakdown(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Return aggregated spending by category."""
        if not self.db:
            raise RuntimeError("Database session required for query execution")

        from app.database.models.transaction import Category

        query = (
            select(
                Category.name.label("category_name"),
                func.sum(Transaction.debit_amount).label("total_spent"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .join(Category, Transaction.category_id == Category.id, isouter=True)
            .where(
                Transaction.user_id == self.user_id,
                Transaction.transaction_kind == TransactionKind.EXPENSE,
            )
        )

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        query = query.group_by(Category.name).order_by(func.sum(Transaction.debit_amount).desc())

        res = await self.db.execute(query)
        rows = res.all()

        total_expenses = sum([r.total_spent or Decimal("0.00") for r in rows], Decimal("0.00"))

        breakdown = []
        for r in rows:
            name = r.category_name or "Other / Uncategorized"
            spent = r.total_spent or Decimal("0.00")
            pct = (float(spent / total_expenses) * 100.0) if total_expenses > 0 else 0.0
            breakdown.append({
                "category": name,
                "amount": spent,
                "count": r.transaction_count,
                "percentage": round(pct, 2),
            })

        return breakdown

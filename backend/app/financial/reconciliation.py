from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.statement import Statement
from app.database.models.transaction import Transaction


class ReconciliationService:
    """Verifies internal ledger consistency and flags account balance discrepancies."""

    def __init__(self, db: AsyncSession, user_id):
        self.db = db
        self.user_id = user_id

    async def reconcile_statement(self, statement_id) -> Dict[str, Any]:
        stmt_res = await self.db.execute(
            select(Statement).where(
                Statement.id == statement_id,
                Statement.user_id == self.user_id,
            )
        )
        statement = stmt_res.scalar_one_or_none()
        if not statement:
            return {"status": "ERROR", "message": "Statement not found"}

        # Fetch all transactions linked to statement ordered by date and id
        tx_res = await self.db.execute(
            select(Transaction)
            .where(
                Transaction.statement_id == statement_id,
                Transaction.user_id == self.user_id,
            )
            .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
        )
        transactions = tx_res.scalars().all()

        total_credits = sum((tx.credit_amount for tx in transactions), Decimal("0.00"))
        total_debits = sum((tx.debit_amount for tx in transactions), Decimal("0.00"))

        opening = statement.opening_balance or Decimal("0.00")
        closing = statement.closing_balance or Decimal("0.00")
        expected_closing = opening + total_credits - total_debits

        discrepancy = abs(expected_closing - closing) if statement.closing_balance is not None else Decimal("0.00")
        is_balanced = discrepancy <= Decimal("0.01")

        # Check line-by-line running balance continuity
        continuity_breaks = []
        for i in range(1, len(transactions)):
            prev_tx = transactions[i - 1]
            curr_tx = transactions[i]
            if prev_tx.balance_after is not None and curr_tx.balance_after is not None:
                expected_curr_bal = prev_tx.balance_after + curr_tx.credit_amount - curr_tx.debit_amount
                if abs(expected_curr_bal - curr_tx.balance_after) > Decimal("0.01"):
                    continuity_breaks.append({
                        "transaction_id": str(curr_tx.id),
                        "date": str(curr_tx.transaction_date),
                        "expected": str(expected_curr_bal),
                        "stated": str(curr_tx.balance_after),
                    })

        return {
            "statement_id": str(statement_id),
            "is_balanced": is_balanced,
            "opening_balance": str(opening),
            "closing_balance": str(closing),
            "total_credits": str(total_credits),
            "total_debits": str(total_debits),
            "expected_closing": str(expected_closing),
            "discrepancy": str(discrepancy),
            "continuity_breaks_count": len(continuity_breaks),
            "continuity_breaks": continuity_breaks,
        }

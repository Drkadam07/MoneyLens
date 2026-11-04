from datetime import date, timedelta
from typing import Any, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.statement import Statement, StatementStatus
from app.database.models.transaction import Transaction


class CoverageService:
    """Analyzes bank statement coverage to prevent mistaking missing periods for ₹0 spend."""

    def __init__(self, db: AsyncSession, user_id):
        self.db = db
        self.user_id = user_id

    async def get_coverage_report(self, start_date: date, end_date: date) -> Dict[str, Any]:
        # 1. Fetch confirmed statements that overlap with [start_date, end_date]
        stmt_res = await self.db.execute(
            select(Statement).where(
                Statement.user_id == self.user_id,
                Statement.status.in_([StatementStatus.CONFIRMED, StatementStatus.ANALYZED]),
                Statement.period_start.is_not(None),
                Statement.period_end.is_not(None),
            )
        )
        statements = stmt_res.scalars().all()

        covered_dates = set()
        for s in statements:
            p_start = max(s.period_start, start_date)
            p_end = min(s.period_end, end_date)
            curr = p_start
            while curr <= p_end:
                covered_dates.add(curr)
                curr += timedelta(days=1)

        # 2. Fetch days with actual transactions
        tx_res = await self.db.execute(
            select(Transaction.transaction_date).where(
                Transaction.user_id == self.user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            ).distinct()
        )
        transaction_dates = set(tx_res.scalars().all())

        # Total requested days
        total_days = (end_date - start_date).days + 1
        covered_days_count = len(covered_dates)
        coverage_pct = (covered_days_count / total_days * 100.0) if total_days > 0 else 0.0

        # Find missing date intervals
        missing_periods = []
        in_gap = False
        gap_start = None

        curr = start_date
        while curr <= end_date:
            if curr not in covered_dates:
                if not in_gap:
                    in_gap = True
                    gap_start = curr
            else:
                if in_gap:
                    in_gap = False
                    missing_periods.append({
                        "start_date": str(gap_start),
                        "end_date": str(curr - timedelta(days=1)),
                        "days": (curr - gap_start).days,
                    })
            curr += timedelta(days=1)

        if in_gap and gap_start is not None:
            missing_periods.append({
                "start_date": str(gap_start),
                "end_date": str(end_date),
                "days": (end_date - gap_start).days + 1,
            })

        return {
            "requested_period": {"start_date": str(start_date), "end_date": str(end_date)},
            "total_days": total_days,
            "covered_days": covered_days_count,
            "coverage_percentage": round(coverage_pct, 2),
            "is_complete": len(missing_periods) == 0,
            "missing_periods": missing_periods,
            "days_with_transactions": len(transaction_dates),
            "days_zero_spend_with_coverage": covered_days_count - len(transaction_dates),
        }

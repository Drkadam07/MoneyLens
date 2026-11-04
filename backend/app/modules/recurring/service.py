import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.database.models.planning import RecurringPayment
from app.database.models.transaction import Transaction, TransactionKind
from app.modules.recurring.schemas import RecurringPaymentResponse


class RecurringPaymentService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_recurring(self) -> List[RecurringPaymentResponse]:
        # First ensure automatic detection runs
        await self.detect_recurring_candidates()

        stmt = (
            select(RecurringPayment)
            .options(
                selectinload(RecurringPayment.merchant),
                selectinload(RecurringPayment.category),
            )
            .where(RecurringPayment.user_id == self.user_id)
            .order_by(RecurringPayment.confidence.desc())
        )
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        return [
            RecurringPaymentResponse(
                id=item.id,
                title=item.title,
                expected_amount=item.expected_amount,
                frequency=item.frequency,
                next_expected_date=item.next_expected_date,
                status=item.status,
                confidence=item.confidence,
                user_confirmed=item.user_confirmed,
                merchant_name=item.merchant.display_name if item.merchant else None,
                category_name=item.category.name if item.category else None,
            )
            for item in items
        ]

    async def detect_recurring_candidates(self) -> None:
        """Analyze transaction history to identify candidates recurring monthly or weekly."""
        tx_res = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.transaction_kind == TransactionKind.EXPENSE,
            ).order_by(Transaction.transaction_date.asc())
        )
        transactions = tx_res.scalars().all()

        # Group by description_normalized
        groups = {}
        for tx in transactions:
            key = tx.description_normalized.lower()
            groups.setdefault(key, []).append(tx)

        for desc_key, tx_list in groups.items():
            if len(tx_list) < 2:
                continue

            # Check intervals between dates
            intervals = []
            for i in range(1, len(tx_list)):
                diff = (tx_list[i].transaction_date - tx_list[i - 1].transaction_date).days
                intervals.append(diff)

            # Check if monthly (interval around 27-33 days)
            avg_interval = sum(intervals) / len(intervals)
            is_monthly = any(27 <= inv <= 33 for inv in intervals)
            is_weekly = any(6 <= inv <= 8 for inv in intervals)

            if is_monthly or is_weekly:
                latest = tx_list[-1]
                freq = "MONTHLY" if is_monthly else "WEEKLY"
                days_to_add = 30 if is_monthly else 7
                next_date = latest.transaction_date + timedelta(days=days_to_add)

                # Check if already saved
                existing = await self.db.execute(
                    select(RecurringPayment).where(
                        RecurringPayment.user_id == self.user_id,
                        RecurringPayment.title == latest.description_normalized,
                    )
                )
                if not existing.scalar_one_or_none():
                    rec = RecurringPayment(
                        user_id=self.user_id,
                        merchant_id=latest.merchant_id,
                        category_id=latest.category_id,
                        title=latest.description_normalized,
                        expected_amount=latest.debit_amount,
                        frequency=freq,
                        next_expected_date=next_date,
                        confidence=0.88,
                        user_confirmed=False,
                    )
                    self.db.add(rec)

        await self.db.commit()

    async def confirm_recurring(self, item_id: uuid.UUID, confirmed: bool) -> RecurringPaymentResponse:
        stmt = select(RecurringPayment).where(
            RecurringPayment.id == item_id,
            RecurringPayment.user_id == self.user_id,
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            raise NotFoundError(f"Recurring payment candidate '{item_id}' not found")

        item.user_confirmed = confirmed
        item.status = "ACTIVE" if confirmed else "DISMISSED"
        await self.db.commit()
        await self.db.refresh(item)

        return RecurringPaymentResponse(
            id=item.id,
            title=item.title,
            expected_amount=item.expected_amount,
            frequency=item.frequency,
            next_expected_date=item.next_expected_date,
            status=item.status,
            confidence=item.confidence,
            user_confirmed=item.user_confirmed,
        )

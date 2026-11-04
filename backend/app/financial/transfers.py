from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.transaction import Transaction, TransactionKind, TransactionTransfer


class TransferDetectionService:
    """Identifies self-transfers between different bank accounts of the same user.
    
    Prevents double-counting: an internal transfer is neither new income nor new expense.
    """

    def __init__(self, db: AsyncSession, user_id):
        self.db = db
        self.user_id = user_id

    async def scan_and_link_transfers(self) -> List[Dict[str, Any]]:
        """Find debit transactions on one account that match credit transactions on another within +/- 1 day."""
        # 1. Fetch unlinked debits and credits
        debits_res = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.debit_amount > Decimal("0.00"),
                Transaction.transaction_kind.in_([TransactionKind.EXPENSE, TransactionKind.TRANSFER, TransactionKind.UNCLASSIFIED]),
            )
        )
        debits = debits_res.scalars().all()

        credits_res = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.credit_amount > Decimal("0.00"),
                Transaction.transaction_kind.in_([TransactionKind.INCOME, TransactionKind.TRANSFER, TransactionKind.UNCLASSIFIED]),
            )
        )
        credits = credits_res.scalars().all()

        detected_transfers = []

        for deb in debits:
            for cred in credits:
                # Must be different accounts
                if deb.account_id == cred.account_id:
                    continue

                # Exact same amount
                if deb.debit_amount == cred.credit_amount:
                    # Date tolerance: same day or within 1 day
                    date_diff = abs((deb.transaction_date - cred.transaction_date).days)
                    if date_diff <= 1:
                        # Check if already linked
                        existing_transfer = await self.db.execute(
                            select(TransactionTransfer).where(
                                TransactionTransfer.source_transaction_id == deb.id,
                                TransactionTransfer.destination_transaction_id == cred.id,
                            )
                        )
                        if not existing_transfer.scalar_one_or_none():
                            transfer_rec = TransactionTransfer(
                                user_id=self.user_id,
                                source_transaction_id=deb.id,
                                destination_transaction_id=cred.id,
                                transfer_status="DETECTED",
                                confidence=0.95 if date_diff == 0 else 0.85,
                                confirmed_by_user=False,
                            )
                            self.db.add(transfer_rec)

                            # Reclassify transactions to TRANSFER so they are excluded from income/expense
                            deb.transaction_kind = TransactionKind.TRANSFER
                            cred.transaction_kind = TransactionKind.TRANSFER

                            detected_transfers.append({
                                "source_tx_id": str(deb.id),
                                "destination_tx_id": str(cred.id),
                                "amount": float(deb.debit_amount),
                                "date": str(deb.transaction_date),
                                "confidence": transfer_rec.confidence,
                            })

        if detected_transfers:
            await self.db.commit()

        return detected_transfers

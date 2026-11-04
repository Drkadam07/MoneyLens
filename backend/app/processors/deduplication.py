import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.transaction import Transaction


class TransactionDeduplicator:
    """Detects potential duplicate transactions across uploaded statements and existing ledger records."""

    def __init__(self, db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.account_id = account_id

    async def detect_duplicates(
        self, candidate_records: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], Optional[Dict[str, Any]], float]]:
        """Compare candidate rows against existing database transactions.
        
        Returns a list of tuples: (candidate_record, matched_existing_tx, match_confidence_score).
        """
        results = []

        # Fetch existing transactions for this user and account
        stmt = (
            select(Transaction)
            .where(
                Transaction.user_id == self.user_id,
                Transaction.account_id == self.account_id,
            )
        )
        existing_res = await self.db.execute(stmt)
        existing_txs = existing_res.scalars().all()

        # Build index lookups for fast comparison
        ref_lookup: Dict[str, Transaction] = {
            tx.reference_number: tx for tx in existing_txs if tx.reference_number
        }

        for cand in candidate_records:
            cand_ref = cand.get("reference_number")
            cand_date = cand.get("transaction_date")
            cand_debit = Decimal(str(cand.get("debit_amount", 0)))
            cand_credit = Decimal(str(cand.get("credit_amount", 0)))
            cand_desc = cand.get("description_normalized", "").strip().lower()

            matched_tx = None
            confidence = 0.0

            # Level 1: Exact bank reference number match
            if cand_ref and cand_ref in ref_lookup:
                matched_tx = ref_lookup[cand_ref]
                confidence = 1.0

            # Level 2: Exact date + amount + description match
            if not matched_tx:
                for tx in existing_txs:
                    if tx.transaction_date == cand_date:
                        if tx.debit_amount == cand_debit and tx.credit_amount == cand_credit:
                            if tx.description_normalized.lower() == cand_desc:
                                matched_tx = tx
                                confidence = 0.95
                                break
                            elif cand_desc in tx.description_normalized.lower() or tx.description_normalized.lower() in cand_desc:
                                matched_tx = tx
                                confidence = 0.85
                                break

            # Format match details
            match_info = None
            if matched_tx:
                match_info = {
                    "existing_id": str(matched_tx.id),
                    "date": str(matched_tx.transaction_date),
                    "description": matched_tx.description_normalized,
                    "debit": float(matched_tx.debit_amount),
                    "credit": float(matched_tx.credit_amount),
                    "reference": matched_tx.reference_number,
                }

            results.append((cand, match_info, confidence))

        return results

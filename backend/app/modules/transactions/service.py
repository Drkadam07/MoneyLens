import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.database.models.transaction import (
    Category,
    ClassificationSource,
    Merchant,
    ReviewStatus,
    Transaction,
    TransactionClassification,
    TransactionKind,
    TransactionNote,
)
from app.modules.transactions.schemas import (
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)


class TransactionService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        payment_method: Optional[str] = None,
        transaction_kind: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> TransactionListResponse:
        query = (
            select(Transaction)
            .options(
                selectinload(Transaction.merchant),
                selectinload(Transaction.category),
            )
            .where(Transaction.user_id == self.user_id)
        )

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)
        if account_id:
            query = query.where(Transaction.account_id == account_id)
        if category_id:
            query = query.where(Transaction.category_id == category_id)
        if payment_method:
            query = query.where(Transaction.payment_method == payment_method)
        if transaction_kind:
            query = query.where(Transaction.transaction_kind == transaction_kind)
        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.where(
                Transaction.description_normalized.ilike(pattern)
                | Transaction.description_original.ilike(pattern)
                | Transaction.reference_number.ilike(pattern)
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        # Pagination & sorting
        offset = (page - 1) * page_size
        query = query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc()).offset(offset).limit(page_size)

        res = await self.db.execute(query)
        txs = res.scalars().all()

        items = [
            TransactionResponse(
                id=t.id,
                account_id=t.account_id,
                statement_id=t.statement_id,
                transaction_date=t.transaction_date,
                description_original=t.description_original,
                description_normalized=t.description_normalized,
                debit_amount=t.debit_amount,
                credit_amount=t.credit_amount,
                currency=t.currency,
                balance_after=t.balance_after,
                reference_number=t.reference_number,
                payment_method=t.payment_method,
                transaction_kind=t.transaction_kind,
                review_status=t.review_status,
                merchant_name=t.merchant.display_name if t.merchant else None,
                category_name=t.category.name if t.category else None,
                notes=t.notes,
                created_at=t.created_at,
            )
            for t in txs
        ]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return TransactionListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_transaction(self, tx_id: uuid.UUID) -> TransactionResponse:
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.merchant),
                selectinload(Transaction.category),
            )
            .where(
                Transaction.id == tx_id,
                Transaction.user_id == self.user_id,
            )
        )
        res = await self.db.execute(stmt)
        t = res.scalar_one_or_none()
        if not t:
            raise NotFoundError(f"Transaction '{tx_id}' not found")

        return TransactionResponse(
            id=t.id,
            account_id=t.account_id,
            statement_id=t.statement_id,
            transaction_date=t.transaction_date,
            description_original=t.description_original,
            description_normalized=t.description_normalized,
            debit_amount=t.debit_amount,
            credit_amount=t.credit_amount,
            currency=t.currency,
            balance_after=t.balance_after,
            reference_number=t.reference_number,
            payment_method=t.payment_method,
            transaction_kind=t.transaction_kind,
            review_status=t.review_status,
            merchant_name=t.merchant.display_name if t.merchant else None,
            category_name=t.category.name if t.category else None,
            notes=t.notes,
            created_at=t.created_at,
        )

    async def update_transaction(self, tx_id: uuid.UUID, data: TransactionUpdate) -> TransactionResponse:
        stmt = select(Transaction).where(
            Transaction.id == tx_id,
            Transaction.user_id == self.user_id,
        )
        res = await self.db.execute(stmt)
        t = res.scalar_one_or_none()
        if not t:
            raise NotFoundError(f"Transaction '{tx_id}' not found")

        if data.category_id is not None:
            t.category_id = data.category_id
            # Record user confirmed classification
            classification = TransactionClassification(
                transaction_id=t.id,
                category_id=data.category_id,
                confidence=1.0,
                classification_source=ClassificationSource.USER,
                is_user_confirmed=True,
            )
            self.db.add(classification)

        if data.notes is not None:
            t.notes = data.notes
        if data.transaction_kind is not None:
            t.transaction_kind = data.transaction_kind
        if data.review_status is not None:
            t.review_status = data.review_status

        await self.db.commit()
        return await self.get_transaction(tx_id)

    async def add_note(self, tx_id: uuid.UUID, note_text: str) -> None:
        stmt = select(Transaction).where(
            Transaction.id == tx_id,
            Transaction.user_id == self.user_id,
        )
        res = await self.db.execute(stmt)
        t = res.scalar_one_or_none()
        if not t:
            raise NotFoundError(f"Transaction '{tx_id}' not found")

        note = TransactionNote(
            transaction_id=tx_id,
            user_id=self.user_id,
            note=note_text,
        )
        self.db.add(note)
        t.notes = note_text
        await self.db.commit()

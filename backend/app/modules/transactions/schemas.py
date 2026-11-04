import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from app.database.models.transaction import PaymentMethod, ReviewStatus, TransactionKind


class TransactionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    statement_id: Optional[uuid.UUID]
    transaction_date: date
    description_original: str
    description_normalized: str
    debit_amount: Decimal
    credit_amount: Decimal
    currency: str
    balance_after: Optional[Decimal]
    reference_number: Optional[str]
    payment_method: PaymentMethod
    transaction_kind: TransactionKind
    review_status: ReviewStatus
    merchant_name: Optional[str] = None
    category_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionUpdate(BaseModel):
    category_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    transaction_kind: Optional[TransactionKind] = None
    review_status: Optional[ReviewStatus] = None


class CategoryUpdate(BaseModel):
    category_id: uuid.UUID


class NoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=1000)

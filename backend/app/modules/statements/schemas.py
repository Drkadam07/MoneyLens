# backend/app/modules/statements/schemas.py
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.database.models.statement import StatementStatus


class StatementUploadResponse(BaseModel):
    statement_id: uuid.UUID
    job_id: uuid.UUID
    status: StatementStatus
    message: str


class StatementWarningResponse(BaseModel):
    id: uuid.UUID
    row_number: int
    warning_type: str
    message: str
    resolution_status: str

    class Config:
        from_attributes = True


class StatementResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    original_filename: str
    file_type: str
    period_start: Optional[date]
    period_end: Optional[date]
    opening_balance: Optional[Decimal]
    closing_balance: Optional[Decimal]
    status: StatementStatus
    created_at: datetime
    warnings_count: int = 0

    class Config:
        from_attributes = True


class StatementJobStatusResponse(BaseModel):
    job_id: uuid.UUID
    statement_id: uuid.UUID
    status: StatementStatus
    total_rows: int
    processed_rows: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class StatementPreviewRow(BaseModel):
    row_number: int
    transaction_date: date
    description_original: str
    description_normalized: str
    debit_amount: Decimal
    credit_amount: Decimal
    balance_after: Optional[Decimal] = None
    reference_number: Optional[str] = None
    payment_method: str
    transaction_kind: str
    merchant_guess: Optional[str] = None
    is_duplicate_candidate: bool = False
    duplicate_confidence: float = 0.0
    duplicate_match_details: Optional[Dict[str, Any]] = None


class StatementPreviewResponse(BaseModel):
    statement_id: uuid.UUID
    status: StatementStatus
    total_records: int
    rows: List[StatementPreviewRow]
    warnings: List[StatementWarningResponse]


class StatementConfirmRequest(BaseModel):
    confirmed_row_numbers: Optional[List[int]] = Field(
        None, description="List of row numbers to confirm. If null, all rows are imported."
    )

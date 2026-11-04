import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class RecurringPaymentResponse(BaseModel):
    id: uuid.UUID
    title: str
    expected_amount: Decimal
    frequency: str
    next_expected_date: date
    status: str
    confidence: float
    user_confirmed: bool
    merchant_name: Optional[str] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class RecurringConfirmRequest(BaseModel):
    user_confirmed: bool = True

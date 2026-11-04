import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BankAccountCreate(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=100)
    account_label: str = Field(..., min_length=2, max_length=100)
    account_type: str = Field(default="SAVINGS", max_length=50)
    masked_account_number: str = Field(..., min_length=4, max_length=20)
    currency: str = Field(default="INR", max_length=10)


class BankAccountUpdate(BaseModel):
    account_label: Optional[str] = Field(None, min_length=2, max_length=100)
    account_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class BankAccountResponse(BaseModel):
    id: uuid.UUID
    bank_name: str
    account_label: str
    account_type: str
    masked_account_number: str
    currency: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    period_type: str = "MONTHLY"
    start_date: date
    end_date: date


class BudgetUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class BudgetProgressResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    amount_budgeted: Decimal
    amount_spent: Decimal
    amount_remaining: Decimal
    percentage_used: float
    start_date: date
    end_date: date
    is_overbudget: bool

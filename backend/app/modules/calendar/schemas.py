from datetime import date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel


class CalendarTransactionItem(BaseModel):
    id: str
    description: str
    amount: Decimal
    kind: str
    category: Optional[str] = None


class CalendarDaySummary(BaseModel):
    date: str
    day: int
    has_coverage: bool
    total_expense: Decimal
    total_income: Decimal
    net_cash_flow: Decimal
    transaction_count: int
    spending_intensity: int  # 0 to 4
    transactions: List[CalendarTransactionItem]


class FinancialCalendarResponse(BaseModel):
    year: int
    month: int
    month_name: str
    total_monthly_expense: Decimal
    total_monthly_income: Decimal
    highest_spending_day: Optional[str]
    days: List[CalendarDaySummary]

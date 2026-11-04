from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PeriodSchema(BaseModel):
    start_date: Optional[str]
    end_date: Optional[str]


class FinancialSummaryResponse(BaseModel):
    period: PeriodSchema
    currency: str
    income: Decimal
    expenses: Decimal
    net_cash_flow: Decimal
    savings_rate_pct: float
    total_debits: Decimal
    total_credits: Decimal
    transfers_excluded: Decimal
    refunds_total: Decimal
    investments_total: Decimal
    unclassified_amount: Decimal
    transaction_count: int
    average_expense: Decimal
    highest_expense: Decimal


class CategoryItem(BaseModel):
    category: str
    amount: Decimal
    count: int
    percentage: float


class DailySpendingPoint(BaseModel):
    date: str
    income: Decimal
    expense: Decimal
    net: Decimal
    count: int


class MonthlySpendingPoint(BaseModel):
    month: str
    income: Decimal
    expense: Decimal
    net: Decimal
    count: int


class CoverageResponse(BaseModel):
    requested_period: Dict[str, str]
    total_days: int
    covered_days: int
    coverage_percentage: float
    is_complete: bool
    missing_periods: List[Dict[str, Any]]
    days_with_transactions: int
    days_zero_spend_with_coverage: int

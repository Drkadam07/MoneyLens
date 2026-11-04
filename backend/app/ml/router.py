from typing import Annotated, Any, Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.models.transaction import Transaction, TransactionKind
from app.database.session import get_db
from app.financial.calculations import FinancialCalculationService
from app.ml.anomaly_detection.detector import AnomalyDetector
from app.ml.categorization.classifier import HybridCategorizer
from app.ml.forecasting.forecaster import ExpenseForecaster
from app.modules.analytics.service import AnalyticsService

router = APIRouter(tags=["Machine Learning & Predictions"])


class ClassifyRequest(BaseModel):
    narration: str


@router.post("/ml/classify")
async def classify_narration(
    request: ClassifyRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    categorizer = HybridCategorizer.get_instance()
    return categorizer.predict(request.narration)


@router.get("/anomalies")
async def get_spending_anomalies(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Fetch user transactions
    tx_res = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.transaction_kind == TransactionKind.EXPENSE,
        ).order_by(Transaction.transaction_date.desc()).limit(100)
    )
    txs = tx_res.scalars().all()

    amounts = [float(t.debit_amount) for t in txs]
    descs = [t.description_normalized for t in txs]

    detector = AnomalyDetector()
    zscore_anomalies = detector.detect_amount_outliers_zscore(amounts, descs)
    mad_anomalies = detector.detect_amount_outliers_mad(amounts, descs)

    return {
        "total_analyzed": len(txs),
        "zscore_anomalies": zscore_anomalies,
        "mad_anomalies": mad_anomalies,
    }


@router.get("/forecasts/expenses")
async def get_expense_forecast(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    analytics = AnalyticsService(db, current_user.id)
    monthly_series = await analytics.get_monthly_series()

    monthly_data = [
        {"month": m.month, "total_expenses": float(m.expense)}
        for m in monthly_series
    ]

    forecaster = ExpenseForecaster()
    return forecaster.forecast_monthly_expenses(monthly_data)

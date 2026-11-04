from decimal import Decimal
from typing import Any, Dict, List, Optional
import numpy as np


class ExpenseForecaster:
    """Forecasts next-month expenses with uncertainty intervals and data sufficiency validation."""

    MIN_MONTHS_REQUIRED = 3

    def forecast_monthly_expenses(
        self,
        monthly_expenses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """monthly_expenses: sorted list of dicts [{'month': '2026-07', 'total_expenses': 24000.00}, ...]"""
        if len(monthly_expenses) < self.MIN_MONTHS_REQUIRED:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": (
                    f"Forecasting requires at least {self.MIN_MONTHS_REQUIRED} months of consecutive "
                    f"statement data. Currently available: {len(monthly_expenses)} month(s)."
                ),
                "predicted_amount": None,
                "lower_bound": None,
                "upper_bound": None,
                "data_quality": "INSUFFICIENT",
            }

        amounts = [float(m["total_expenses"]) for m in monthly_expenses]
        arr = np.array(amounts)

        # 1. Moving average baseline
        moving_avg = float(np.mean(arr[-3:]))

        # 2. Linear trend slope
        x = np.arange(len(arr))
        slope, intercept = np.polyfit(x, arr, 1)

        # Next period index
        next_x = len(arr)
        trend_prediction = float(slope * next_x + intercept)

        # Blend moving average with trend (70% trend, 30% recent average)
        blended_forecast = max(0.0, 0.7 * trend_prediction + 0.3 * moving_avg)

        # Standard error / volatility for prediction interval
        residuals = arr - (slope * x + intercept)
        rmse = float(np.std(residuals)) if len(residuals) > 0 else 0.1 * blended_forecast
        confidence_margin = 1.96 * max(rmse, 0.05 * blended_forecast)

        lower_bound = max(0.0, blended_forecast - confidence_margin)
        upper_bound = blended_forecast + confidence_margin

        return {
            "status": "SUCCESS",
            "predicted_amount": round(Decimal(str(blended_forecast)), 2),
            "lower_bound": round(Decimal(str(lower_bound)), 2),
            "upper_bound": round(Decimal(str(upper_bound)), 2),
            "currency": "INR",
            "model_version": "trend-ma-v1",
            "data_quality": "SUFFICIENT",
            "historical_months_used": len(monthly_expenses),
        }

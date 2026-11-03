from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.accounts.router import router as accounts_router
from app.modules.statements.router import router as statements_router
from app.modules.transactions.router import router as transactions_router
from app.modules.analytics.router import router as analytics_router
from app.modules.calendar.router import router as calendar_router
from app.modules.budgets.router import router as budgets_router
from app.modules.recurring.router import router as recurring_router
from app.ai.router import router as ai_router
from app.ml.router import router as ml_router

api_router = APIRouter(prefix="/api/v1")

# Health check
@api_router.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "MoneyLens API",
        "version": "1.0.0",
        "deterministic_engine": "ACTIVE",
    }

api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(statements_router)
api_router.include_router(transactions_router)
api_router.include_router(analytics_router)
api_router.include_router(calendar_router)
api_router.include_router(budgets_router)
api_router.include_router(recurring_router)
api_router.include_router(ai_router)
api_router.include_router(ml_router)

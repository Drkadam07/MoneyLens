from typing import Annotated, Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.finance_agent import FinanceAgentOrchestrator
from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    intent: str
    period: Dict[str, Optional[str]]
    currency: str
    evidence: Dict[str, Any]
    data_warnings: list[str]
    visualization: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    orchestrator = FinanceAgentOrchestrator(db, current_user.id)
    result = await orchestrator.execute(request.message)
    return ChatResponse(**result)

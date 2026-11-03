from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.intelligence import KnowledgeChunk, KnowledgeDocument

FINANCIAL_DEFINITIONS = {
    "net cash flow": (
        "Net Cash Flow is the total classified income minus total classified expenses over a given period. "
        "Unlike raw balance changes, it strictly excludes self-transfers between your own accounts and investment deposits."
    ),
    "debit": (
        "In MoneyLens, a debit represents money leaving an account, but it is not automatically an expense. "
        "For example, an ATM cash withdrawal or an internal self-transfer is a debit, but not a consumption expense."
    ),
    "credit": (
        "In MoneyLens, a credit represents money entering an account, but it is not automatically income. "
        "For example, a refund for a returned product or an internal transfer from another account is not income."
    ),
    "reconciliation": (
        "Reconciliation validates that: Opening Balance + Total Credits - Total Debits = Closing Balance. "
        "MoneyLens flags any discrepancy for audit rather than silently adjusting your financial transactions."
    ),
    "upi": (
        "Unified Payments Interface (UPI) is a payment method, not an expense category. "
        "A UPI transaction can simultaneously be an Expense in Food & Dining with merchant Swiggy."
    ),
}


class KnowledgeRetriever:
    """Retrieves authoritative financial definitions and help documents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve_relevant_knowledge(self, query: str) -> List[str]:
        q_lower = query.lower()
        matched = []

        # 1. Match local financial definitions
        for term, definition in FINANCIAL_DEFINITIONS.items():
            if term in q_lower:
                matched.append(f"Definition of {term.title()}: {definition}")

        # 2. Query knowledge_chunks table
        stmt = select(KnowledgeChunk).limit(3)
        res = await self.db.execute(stmt)
        chunks = res.scalars().all()
        for c in chunks:
            if any(word in c.chunk_text.lower() for word in q_lower.split() if len(word) > 4):
                matched.append(c.chunk_text)

        return matched

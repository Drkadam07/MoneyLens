import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_provider import LLMProvider
from app.ai.rag.retriever import KnowledgeRetriever
from app.ai.tools.financial_tools import FinancialToolBelt


class FinanceAgentState(TypedDict):
    user_id: uuid.UUID
    question: str
    intent: str
    date_range: Dict[str, Optional[date]]
    tool_results: Dict[str, Any]
    retrieved_knowledge: List[str]
    data_warnings: List[str]
    final_answer: str
    evidence: Dict[str, Any]
    visualization: Optional[Dict[str, Any]]


class FinanceAgentOrchestrator:
    """Agentic AI workflow orchestrator using structured state and deterministic tools."""

    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.tools = FinancialToolBelt(db, user_id)
        self.retriever = KnowledgeRetriever(db)
        self.llm = LLMProvider()

    async def execute(self, question: str) -> Dict[str, Any]:
        """Run the end-to-end grounded agent workflow."""
        state: FinanceAgentState = {
            "user_id": self.user_id,
            "question": question,
            "intent": "general",
            "date_range": {"start_date": None, "end_date": None},
            "tool_results": {},
            "retrieved_knowledge": [],
            "data_warnings": [],
            "final_answer": "",
            "evidence": {},
            "visualization": None,
        }

        # Step 1: Intent Routing & Parameter Extraction
        state = self._route_intent(state)

        # Step 2: Tool Execution
        state = await self._execute_tools(state)

        # Step 3: Knowledge Retrieval
        state = await self._retrieve_knowledge(state)

        # Step 4: Evidence Validation
        state = self._validate_evidence(state)

        # Step 5: Natural Language Synthesis
        state = await self._synthesize_response(state)

        return {
            "answer": state["final_answer"],
            "intent": state["intent"],
            "period": {
                "start": str(state["date_range"]["start_date"]) if state["date_range"]["start_date"] else None,
                "end": str(state["date_range"]["end_date"]) if state["date_range"]["end_date"] else None,
            },
            "currency": "INR",
            "evidence": state["evidence"],
            "data_warnings": state["data_warnings"],
            "visualization": state["visualization"],
        }

    def _route_intent(self, state: FinanceAgentState) -> FinanceAgentState:
        q = state["question"].lower()

        # Date heuristic extraction
        now = datetime.now()
        start = None
        end = None

        if "this month" in q:
            start = date(now.year, now.month, 1)
            end = now.date()
        elif "last month" in q:
            first_this_month = date(now.year, now.month, 1)
            last_prev_month = first_this_month - timedelta(days=1)
            start = date(last_prev_month.year, last_prev_month.month, 1)
            end = last_prev_month
        elif "october" in q:
            start = date(2026, 10, 1)
            end = date(2026, 10, 31)
        elif "september" in q:
            start = date(2026, 9, 1)
            end = date(2026, 9, 30)

        state["date_range"] = {"start_date": start, "end_date": end}

        # Intent categorization
        if any(w in q for w in ["breakdown", "category", "categories", "spend on food", "dining"]):
            state["intent"] = "category_breakdown"
        elif any(w in q for w in ["summary", "net cash", "cash flow", "income", "how much did i spend"]):
            state["intent"] = "financial_summary"
        elif any(w in q for w in ["recurring", "subscription", "bills", "netflix", "sip"]):
            state["intent"] = "recurring_payments"
        elif any(w in q for w in ["compare", "versus", "vs"]):
            state["intent"] = "comparison"
        elif any(w in q for w in ["transactions above", "find transaction", "search", "show all"]):
            state["intent"] = "transaction_search"
        elif any(w in q for w in ["what is", "difference between", "explain", "meaning of"]):
            state["intent"] = "knowledge_query"
        else:
            state["intent"] = "financial_summary"

        return state

    async def _execute_tools(self, state: FinanceAgentState) -> FinanceAgentState:
        intent = state["intent"]
        start = state["date_range"]["start_date"]
        end = state["date_range"]["end_date"]

        if intent == "financial_summary":
            summary = await self.tools.get_financial_summary(start, end)
            state["tool_results"]["summary"] = summary
            state["evidence"] = summary
            state["visualization"] = {
                "type": "summary_cards",
                "data": {
                    "income": summary["income"],
                    "expenses": summary["expenses"],
                    "net_cash_flow": summary["net_cash_flow"],
                },
            }

        elif intent == "category_breakdown":
            breakdown = await self.tools.get_category_breakdown(start, end)
            state["tool_results"]["breakdown"] = breakdown
            state["evidence"] = {"categories": breakdown}
            state["visualization"] = {
                "type": "category_pie",
                "data": breakdown,
            }

        elif intent == "recurring_payments":
            recurr = await self.tools.get_recurring_payments()
            state["tool_results"]["recurring"] = recurr
            state["evidence"] = {"recurring_payments": recurr}
            state["visualization"] = {
                "type": "recurring_list",
                "data": recurr,
            }

        elif intent == "transaction_search":
            # Extract possible amount threshold (e.g. above 5000)
            amt_match = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)", state["question"])
            min_amt = Decimal(amt_match.group(1).replace(",", "")) if amt_match else None
            txs = await self.tools.search_transactions(min_amount=min_amt, start_date=start, end_date=end)
            state["tool_results"]["transactions"] = txs
            state["evidence"] = {"matching_transactions": txs}
            state["visualization"] = {
                "type": "transaction_table",
                "data": txs,
            }

        return state

    async def _retrieve_knowledge(self, state: FinanceAgentState) -> FinanceAgentState:
        docs = await self.retriever.retrieve_relevant_knowledge(state["question"])
        state["retrieved_knowledge"] = docs
        return state

    def _validate_evidence(self, state: FinanceAgentState) -> FinanceAgentState:
        # Check if query returned empty data
        if state["intent"] == "financial_summary":
            summary = state["tool_results"].get("summary", {})
            if summary.get("transaction_count", 0) == 0:
                state["data_warnings"].append(
                    "No transactions recorded for the requested period. Ensure statements are imported."
                )
        return state

    async def _synthesize_response(self, state: FinanceAgentState) -> FinanceAgentState:
        evidence_str = str(state["tool_results"])
        knowledge_str = "\n".join(state["retrieved_knowledge"])
        warnings_str = "\n".join(state["data_warnings"])

        system_prompt = (
            "You are MoneyLens AI, an expert, objective fintech assistant. "
            "CRITICAL RULES:\n"
            "1. ONLY use figures provided in the EVIDENCE section. Never perform your own math or invent numbers.\n"
            "2. State amounts clearly in Indian Rupees (₹).\n"
            "3. If evidence is empty, state that statement data is missing for the given period.\n"
            "4. Keep answers concise, professional, and actionable."
        )

        user_prompt = (
            f"User Question: {state['question']}\n"
            f"Evidence from SQL Ledger:\n{evidence_str}\n"
            f"Retrieved Knowledge:\n{knowledge_str}\n"
            f"Data Warnings:\n{warnings_str}\n"
        )

        llm_text = await self.llm.generate_response(system_prompt, user_prompt)
        state["final_answer"] = llm_text
        return state

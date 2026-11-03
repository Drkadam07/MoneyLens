# MoneyLens — AI-Powered Personal Finance Intelligence Platform

MoneyLens is a production-grade personal finance intelligence platform designed to ingest, clean, validate, and analyze bank statements and UPI transactions. It couples a **deterministic PostgreSQL financial engine** with a **hybrid ML categorization pipeline** and a **LangGraph-driven Agentic AI assistant**.

---

## 🏛️ Core Architectural Principles

1. **Deterministic Single Source of Truth:**
   - PostgreSQL is the sole financial ledger.
   - LLMs and vector databases **never** perform math or invent balances.
   - All currencies and figures use high-precision `NUMERIC(18, 2)` (never IEEE floating point).
2. **Deterministic Financial Accounting:**
   - `Debit != Expense` (e.g. self-transfers, cash withdrawals, investment purchases).
   - `Credit != Income` (e.g. refunds, loan disbursements, transfer between user accounts).
   - `Net Cash Flow = Classified Income - Classified Expenses` (excluding internal transfers).
   - Automated reconciliation verification: $\text{Opening Balance} + \text{Credits} - \text{Debits} = \text{Closing Balance}$. Discrepancies are flagged for audit.
3. **Strict User Isolation:**
   - Every database query, Celery task, and AI agent tool strictly enforces tenant `user_id` authenticated from JWT session tokens.
4. **Decoupled Architecture:**
   - Core financial domain services operate completely independently of the AI layer.
   - The AI Assistant interacts only via authorized, read-only Python/SQL tool primitives.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (Async/Typed), Alembic, Pydantic v2.
- **Database & Storage:** PostgreSQL 16 with `pgvector`, Redis 7 (broker/cache), private local statement storage.
- **Workers:** Celery for background ingestion, validation, and analytics.
- **Document Processing:** PyMuPDF, `pdfplumber`, OpenPyXL, Pandas.
- **ML Engine:** Scikit-learn (TF-IDF + Logistic Regression), Isolation Forest for anomaly detection, Trend/SARIMA forecaster.
- **Agentic AI:** LangGraph, LangChain, Groq/OpenAI/Gemini provider interfaces with grounded structured outputs.
- **Web Frontend:** React 18+, Vite, TypeScript, Tailwind CSS, Lucide React, TanStack Query, Zustand, Recharts.

---

## 🚀 Quick Start (Docker)

```bash
# 1. Clone repository & configure environment
cp .env.example .env

# 2. Boot up full container stack (PostgreSQL + Redis + Backend + Worker + Frontend)
docker-compose up --build

# 3. Seed synthetic Indian banking transactions (UPI, Salary, Rent, Swiggy, etc.)
docker-compose exec backend python seed.py
```

- **Frontend:** http://localhost:5173
- **FastAPI API & Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

---

## 🧪 Testing

```bash
# Run deterministic financial engine and parser tests
cd backend
pytest tests/unit/ -v
```

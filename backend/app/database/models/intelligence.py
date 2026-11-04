import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, CommonMixin, utc_now


class AnomalyEvent(Base, CommonMixin):
    __tablename__ = "anomaly_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    detector: Mapped[str] = mapped_column(String(100), nullable=False)  # ZSCORE, MAD, ISOLATION_FOREST
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default="UNREVIEWED", nullable=False)  # UNREVIEWED, DISMISSED, CONFIRMED
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0", nullable=False)

    transaction = relationship("Transaction")


class ExpenseForecast(Base, CommonMixin):
    __tablename__ = "expense_forecasts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    lower_bound: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    upper_bound: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="trend-v1", nullable=False)
    data_quality: Mapped[str] = mapped_column(String(50), default="SUFFICIENT", nullable=False)


class FinancialInsight(Base, CommonMixin):
    __tablename__ = "financial_insights"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    insight_type: Mapped[str] = mapped_column(String(100), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class KnowledgeDocument(Base, CommonMixin):
    __tablename__ = "knowledge_documents"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)  # HELP_DOC, FINANCIAL_CONCEPT, USER_NOTE
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    chunks: Mapped[List["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base, CommonMixin):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")


class ChatSession(Base, CommonMixin):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="Financial Assistant Chat", nullable=False)

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base, CommonMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_trace: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class AuditLog(Base, CommonMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

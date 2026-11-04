import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, CommonMixin


class StatementStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    VALIDATING = "VALIDATING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED = "CONFIRMED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Statement(Base, CommonMixin):
    __tablename__ = "statements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, csv, xlsx
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SHA-256
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    opening_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    closing_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus),
        default=StatementStatus.QUEUED,
        nullable=False,
        index=True
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships
    account: Mapped["BankAccount"] = relationship("BankAccount", back_populates="statements")
    jobs: Mapped[List["StatementImportJob"]] = relationship(
        "StatementImportJob", back_populates="statement", cascade="all, delete-orphan"
    )
    warnings: Mapped[List["StatementImportWarning"]] = relationship(
        "StatementImportWarning", back_populates="statement", cascade="all, delete-orphan"
    )
    rows: Mapped[List["StatementRow"]] = relationship(
        "StatementRow", back_populates="statement", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="statement"
    )


class StatementImportJob(Base, CommonMixin):
    __tablename__ = "statement_import_jobs"

    statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus),
        default=StatementStatus.QUEUED,
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    statement: Mapped["Statement"] = relationship("Statement", back_populates="jobs")


class StatementImportWarning(Base, CommonMixin):
    __tablename__ = "statement_import_warnings"

    statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_type: Mapped[str] = mapped_column(String(100), nullable=False)  # RECONCILIATION_MISMATCH, DUPLICATE_CANDIDATE, etc.
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(50), default="UNRESOLVED", nullable=False)

    statement: Mapped["Statement"] = relationship("Statement", back_populates="warnings")


class StatementRow(Base, CommonMixin):
    __tablename__ = "statement_rows"

    statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(50), default="PARSED", nullable=False)
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    statement: Mapped["Statement"] = relationship("Statement", back_populates="rows")

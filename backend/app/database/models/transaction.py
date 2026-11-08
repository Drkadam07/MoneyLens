#backend/app/database/models/transaction.py
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, CommonMixin, utc_now


class TransactionKind(str, enum.Enum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    INVESTMENT = "INVESTMENT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    UNCLASSIFIED = "UNCLASSIFIED"


class PaymentMethod(str, enum.Enum):
    UPI = "UPI"
    CARD = "CARD"
    NETBANKING = "NETBANKING"
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"


class ReviewStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DISMISSED = "DISMISSED"


class ClassificationSource(str, enum.Enum):
    RULE = "RULE"
    ML = "ML"
    USER = "USER"


class CategoryType(str, enum.Enum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"


class Transaction(Base, CommonMixin):
    __tablename__ = "transactions"

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
    statement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )

    transaction_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    description_original: Mapped[str] = mapped_column(Text, nullable=False)
    description_normalized: Mapped[str] = mapped_column(String(500), nullable=False)

    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    balance_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    reference_number: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, length=50),
        default=PaymentMethod.OTHER,
        nullable=False,
        index=True
    )
    transaction_kind: Mapped[TransactionKind] = mapped_column(
        Enum(TransactionKind, native_enum=False, length=50),
        default=TransactionKind.UNCLASSIFIED,
        nullable=False,
        index=True
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=50),
        default=ReviewStatus.CONFIRMED,
        nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    statement: Mapped[Optional["Statement"]] = relationship("Statement", back_populates="transactions")
    account: Mapped["BankAccount"] = relationship("BankAccount", back_populates="transactions")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant", back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="transactions")
    classifications: Mapped[List["TransactionClassification"]] = relationship(
        "TransactionClassification", back_populates="transaction", cascade="all, delete-orphan"
    )
    transaction_notes: Mapped[List["TransactionNote"]] = relationship(
        "TransactionNote", back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_user_account", "user_id", "account_id"),
    )


class Category(Base, CommonMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )
    category_type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, native_enum=False, length=50),
        default=CategoryType.EXPENSE,
        nullable=False
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    parent: Mapped[Optional["Category"]] = relationship("Category", remote_side="Category.id", backref="subcategories")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="category")


class TransactionClassification(Base, CommonMixin):
    __tablename__ = "transaction_classifications"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    classification_source: Mapped[ClassificationSource] = mapped_column(
        Enum(ClassificationSource, native_enum=False, length=50),
        default=ClassificationSource.RULE,
        nullable=False
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="classifications")
    category: Mapped["Category"] = relationship("Category")


class Merchant(Base, CommonMixin):
    __tablename__ = "merchants"

    normalized_name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    default_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )

    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="merchant")
    aliases: Mapped[List["MerchantAlias"]] = relationship(
        "MerchantAlias", back_populates="merchant", cascade="all, delete-orphan"
    )


class MerchantAlias(Base, CommonMixin):
    __tablename__ = "merchant_aliases"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    alias: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="SYSTEM", nullable=False)  # SYSTEM, USER
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="aliases")


class UserCategorizationRule(Base, CommonMixin):
    __tablename__ = "user_categorization_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    match_type: Mapped[str] = mapped_column(String(20), default="CONTAINS", nullable=False)  # EXACT, CONTAINS, REGEX
    match_value: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TransactionTransfer(Base, CommonMixin):
    __tablename__ = "transaction_transfers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    source_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    destination_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    transfer_status: Mapped[str] = mapped_column(String(50), default="DETECTED", nullable=False)  # DETECTED, CONFIRMED, REJECTED
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TransactionNote(Base, CommonMixin):
    __tablename__ = "transaction_notes"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="transaction_notes")

from decimal import Decimal
import uuid
from app.processors.validation import StatementValidator



def test_statement_validator_balanced_sequence():
    # Sequence of transactions:
    # Opening: 10,000.00
    # Tx 1: Credit 5,000 -> Bal 15,000
    # Tx 2: Debit 2,000 -> Bal 13,000
    # Tx 3: Debit 500 -> Bal 12,500
    # Closing: 12,500.00

    records = [
        {
            "row_number": 1,
            "transaction_date": "2026-10-01",
            "debit_amount": 0.00,
            "credit_amount": 5000.00,
            "balance_after": 15000.00,
        },
        {
            "row_number": 2,
            "transaction_date": "2026-10-02",
            "debit_amount": 2000.00,
            "credit_amount": 0.00,
            "balance_after": 13000.00,
        },
        {
            "row_number": 3,
            "transaction_date": "2026-10-03",
            "debit_amount": 500.00,
            "credit_amount": 0.00,
            "balance_after": 12500.00,
        },
    ]

    is_valid, warnings = StatementValidator.validate_statement_records(
        records,
        declared_opening_balance=Decimal("10000.00"),
        declared_closing_balance=Decimal("12500.00"),
    )

    assert is_valid is True
    assert len(warnings) == 0


def test_statement_validator_flags_arithmetic_discrepancy():
    # Sequence with discrepancy on row 2:
    # Row 1 stated bal: 15,000
    # Row 2: Debit 2,000, but statement incorrectly prints balance as 14,000 (discrepancy of 1,000)

    records = [
        {
            "row_number": 1,
            "transaction_date": "2026-10-01",
            "debit_amount": 0.00,
            "credit_amount": 5000.00,
            "balance_after": 15000.00,
        },
        {
            "row_number": 2,
            "transaction_date": "2026-10-02",
            "debit_amount": 2000.00,
            "credit_amount": 0.00,
            "balance_after": 14000.00,  # Expected 13,000!
        },
    ]

    is_valid, warnings = StatementValidator.validate_statement_records(
        records,
        declared_opening_balance=Decimal("10000.00"),
        declared_closing_balance=Decimal("13000.00"),
    )

    # Discrepancy must be flagged in warnings
    assert any(w["warning_type"] == "RECONCILIATION_MISMATCH" for w in warnings)
    assert any(w["warning_type"] == "CLOSING_BALANCE_MISMATCH" for w in warnings)

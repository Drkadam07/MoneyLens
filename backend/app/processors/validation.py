import hashlib
from decimal import Decimal
from typing import Any, Dict, List, Tuple


class StatementValidator:
    """Validates statement transactions and enforces financial balance equations."""

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Compute SHA-256 hash of file bytes for idempotency verification."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def validate_statement_records(
        records: List[Dict[str, Any]],
        declared_opening_balance: Decimal | None = None,
        declared_closing_balance: Decimal | None = None,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Validate transaction sequence integrity and balance arithmetic.
        
        Equation: Balance_{n-1} + Credit_n - Debit_n = Balance_n.
        Discrepancies are flagged as warnings without silently altering data.
        """
        warnings = []
        is_valid = True

        if not records:
            warnings.append({
                "row_number": 0,
                "warning_type": "EMPTY_STATEMENT",
                "message": "Statement contains zero valid transaction records.",
            })
            return False, warnings

        # Track sequential balances if present in the data
        previous_balance: Decimal | None = declared_opening_balance

        for i, row in enumerate(records):
            row_num = row.get("row_number", i + 1)
            debit = Decimal(str(row.get("debit_amount", 0)))
            credit = Decimal(str(row.get("credit_amount", 0)))
            balance_after = Decimal(str(row["balance_after"])) if row.get("balance_after") is not None else None

            # 1. Missing transaction date check
            if not row.get("transaction_date"):
                warnings.append({
                    "row_number": row_num,
                    "warning_type": "MISSING_DATE",
                    "message": f"Row {row_num}: Missing transaction date.",
                })
                is_valid = False

            # 2. Both debit and credit present or both zero
            if debit > 0 and credit > 0:
                warnings.append({
                    "row_number": row_num,
                    "warning_type": "AMBIGUOUS_AMOUNT",
                    "message": f"Row {row_num}: Both debit ({debit}) and credit ({credit}) are non-zero.",
                })

            # 3. Balance verification equation
            if previous_balance is not None and balance_after is not None:
                expected_balance = previous_balance + credit - debit
                # Allow tolerance of 0.01 for rounding in statements
                if abs(expected_balance - balance_after) > Decimal("0.01"):
                    warnings.append({
                        "row_number": row_num,
                        "warning_type": "RECONCILIATION_MISMATCH",
                        "message": (
                            f"Row {row_num}: Arithmetic balance mismatch. "
                            f"Previous ({previous_balance}) + Credit ({credit}) - Debit ({debit}) = "
                            f"{expected_balance}, but statement states balance is {balance_after}."
                        ),
                    })
                    # Do not set is_valid to False so that user can review, but warning is recorded

            # Update previous_balance for next row
            if balance_after is not None:
                previous_balance = balance_after

        # 4. Closing balance check against last record
        if declared_closing_balance is not None and previous_balance is not None:
            if abs(previous_balance - declared_closing_balance) > Decimal("0.01"):
                warnings.append({
                    "row_number": len(records),
                    "warning_type": "CLOSING_BALANCE_MISMATCH",
                    "message": (
                        f"Computed final balance {previous_balance} does not match "
                        f"declared closing balance {declared_closing_balance}."
                    ),
                })

        return is_valid, warnings

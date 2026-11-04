import os
import sys
from decimal import Decimal
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.processors.normalization import (
    classify_transaction_kind,
    detect_payment_method,
    extract_merchant,
    normalize_transaction_record,
)
from app.processors.validation import StatementValidator
from tests.unit.test_calculations import test_deterministic_cash_flow_and_transfer_exclusion
from tests.unit.test_reconciliation import (
    test_statement_validator_balanced_sequence,
    test_statement_validator_flags_arithmetic_discrepancy,
)
from tests.unit.test_parsers import (
    test_upi_and_merchant_normalization,
    test_csv_parser_with_sample_file,
)


def run_all_tests():
    print("=" * 70)
    print("Running MoneyLens Deterministic Financial & Parsing Test Suite")
    print("=" * 70)

    # 1. Test normalization
    print(">> Running UPI & Merchant Normalization Tests...", end=" ")
    test_upi_and_merchant_normalization()
    print("PASSED [OK]")

    # 2. Test Reconciliation & Balance Arithmetic
    print(">> Running Reconciliation Sequence Test...", end=" ")
    test_statement_validator_balanced_sequence()
    print("PASSED [OK]")

    print(">> Running Reconciliation Discrepancy Flagging Test...", end=" ")
    test_statement_validator_flags_arithmetic_discrepancy()
    print("PASSED [OK]")

    # 3. Test CSV Parser
    print(">> Running CSV Statement Parser Test...", end=" ")
    test_csv_parser_with_sample_file()
    print("PASSED [OK]")

    # 4. Test Deterministic Calculations (Cash Flow, Transfer Exclusions)
    print(">> Running Deterministic Cash Flow & Transfer Exclusion Tests...", end=" ")
    test_deterministic_cash_flow_and_transfer_exclusion()
    print("PASSED [OK]")

    print("=" * 70)
    print("SUCCESS: ALL 5 TEST SUITES PASSED (100% Deterministic Financial Verifications)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()

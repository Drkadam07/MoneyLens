from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile

from app.processors.csv_parser import CSVStatementParser

from app.processors.normalization import (
    classify_transaction_kind,
    detect_payment_method,
    extract_merchant,
    normalize_transaction_record,
)


def test_upi_and_merchant_normalization():
    # 1. Swiggy UPI
    upi_swiggy = "UPI/DR/SWIGGY/ORDER9872/KOTAK"
    assert detect_payment_method(upi_swiggy) == "UPI"
    assert extract_merchant(upi_swiggy) == "Swiggy"
    assert classify_transaction_kind(upi_swiggy, debit_amount=450.0, credit_amount=0.0) == "EXPENSE"

    # 2. Salary NEFT
    sal = "NEFT-AXIS-ACME LTD-MONTHLY SALARY"
    assert detect_payment_method(sal) == "NETBANKING"
    assert classify_transaction_kind(sal, debit_amount=0.0, credit_amount=85000.0) == "INCOME"

    # 3. ATM Cash Withdrawal (Debit != Expense)
    atm = "ATM WDL/CASH/HDFC ATM BANDRA"
    assert detect_payment_method(atm) == "CASH"
    assert classify_transaction_kind(atm, debit_amount=5000.0, credit_amount=0.0) == "CASH_WITHDRAWAL"

    # 4. Refund (Credit != Income)
    ref = "REFUND/AMAZON PAY RETAIL RETURN"
    assert classify_transaction_kind(ref, debit_amount=0.0, credit_amount=1200.0) == "REFUND"

    # 5. Investment (Zerodha)
    inv = "ACH D-ZERODHA BROKING-SIP"
    assert classify_transaction_kind(inv, debit_amount=10000.0, credit_amount=0.0) == "INVESTMENT"


def test_csv_parser_with_sample_file():
    csv_content = """Date,Narration,Chq/Ref No,Withdrawal,Deposit,Balance
01/10/2026,SALARY CREDIT ACME,NEFT1001,0.00,75000.00,80000.00
02/10/2026,UPI/DR/SWIGGY/ORD1,UPI2001,450.00,0.00,79550.00
03/10/2026,POS 453212XXXXXX1234 STARBUCKS,POS3001,320.00,0.00,79230.00
04/10/2026,ATM WDL CASH HDFC,ATM4001,2000.00,0.00,77230.00
"""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        parser = CSVStatementParser()
        assert parser.can_parse(tmp_path) is True

        extracted = parser.extract(tmp_path)
        assert len(extracted) == 4

        normalized = parser.normalize(extracted)
        assert len(normalized) == 4

        # Validate first row (Salary)
        assert normalized[0]["transaction_date"] == date(2026, 10, 1)
        assert normalized[0]["credit_amount"] == 75000.00
        assert normalized[0]["transaction_kind"] == "INCOME"

        # Validate second row (Swiggy)
        assert normalized[1]["merchant_guess"] == "Swiggy"
        assert normalized[1]["debit_amount"] == 450.00
        assert normalized[1]["payment_method"] == "UPI"
        assert normalized[1]["transaction_kind"] == "EXPENSE"

        # Validate fourth row (ATM)
        assert normalized[3]["transaction_kind"] == "CASH_WITHDRAWAL"
    finally:
        tmp_path.unlink(missing_ok=True)

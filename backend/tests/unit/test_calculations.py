from datetime import date
from decimal import Decimal
import uuid

from app.database.models.transaction import Transaction, TransactionKind, PaymentMethod
from app.financial.calculations import FinancialCalculationService


def test_deterministic_cash_flow_and_transfer_exclusion():
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    # Synthetic transactions:
    # 1. Salary Credit: +50,000 (INCOME)
    # 2. Grocery Expense: -3,500 (EXPENSE)
    # 3. Self-Transfer Debit: -10,000 (TRANSFER) - MUST BE EXCLUDED FROM EXPENSES
    # 4. Self-Transfer Credit: +10,000 (TRANSFER) - MUST BE EXCLUDED FROM INCOME
    # 5. Refund Credit: +1,200 (REFUND) - MUST BE EXCLUDED FROM GENERAL INCOME
    # 6. Investment Debit: -15,000 (INVESTMENT) - EXCLUDED FROM CONSUMPTION EXPENSES
    # 7. Restaurant Expense: -650 (EXPENSE)

    txs = [
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 1),
            description_original="SALARY CREDIT",
            description_normalized="Salary",
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("50000.00"),
            currency="INR",
            payment_method=PaymentMethod.NETBANKING,
            transaction_kind=TransactionKind.INCOME,
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 2),
            description_original="BLINKIT GROCERIES",
            description_normalized="Blinkit",
            debit_amount=Decimal("3500.00"),
            credit_amount=Decimal("0.00"),
            currency="INR",
            payment_method=PaymentMethod.UPI,
            transaction_kind=TransactionKind.EXPENSE,
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 3),
            description_original="TRANSFER TO SAVINGS",
            description_normalized="Self-Transfer",
            debit_amount=Decimal("10000.00"),
            credit_amount=Decimal("0.00"),
            currency="INR",
            payment_method=PaymentMethod.NETBANKING,
            transaction_kind=TransactionKind.TRANSFER,
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 3),
            description_original="TRANSFER FROM CURRENT",
            description_normalized="Self-Transfer",
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("10000.00"),
            currency="INR",
            payment_method=PaymentMethod.NETBANKING,
            transaction_kind=TransactionKind.TRANSFER,
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 5),
            description_original="AMAZON RETURN REFUND",
            description_normalized="Amazon Refund",
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("1200.00"),
            currency="INR",
            payment_method=PaymentMethod.CARD,
            transaction_kind=TransactionKind.REFUND,
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 6),
            description_original="ZERODHA BROKING MUTUAL FUND",
            description_normalized="Zerodha SIP",
            debit_amount=Decimal("15000.00"),
            credit_amount=Decimal("0.00"),
            currency="INR",
            payment_method=PaymentMethod.NETBANKING,
            transaction_kind=TransactionKind.INVESTMENT,
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 10, 7),
            description_original="SWIGGY FOOD ORDER",
            description_normalized="Swiggy",
            debit_amount=Decimal("650.00"),
            credit_amount=Decimal("0.00"),
            currency="INR",
            payment_method=PaymentMethod.UPI,
            transaction_kind=TransactionKind.EXPENSE,
        ),
    ]

    summary = FinancialCalculationService.calculate_summary_from_transactions(txs)

    # Authoritative checks:
    # 1. Income must be exactly ₹50,000 (transfers and refunds excluded)
    assert summary["income"] == Decimal("50000.00")

    # 2. Classified expenses must be exactly ₹3,500 + ₹650 = ₹4,150 (transfers & investments excluded)
    assert summary["expenses"] == Decimal("4150.00")

    # 3. Net cash flow = 50,000 - 4,150 = 45,850.00
    assert summary["net_cash_flow"] == Decimal("45850.00")

    # 4. Transfers excluded sum = 10,000 + 10,000 = 20,000.00
    assert summary["transfers_excluded"] == Decimal("20000.00")

    # 5. Refunds total = 1,200.00
    assert summary["refunds_total"] == Decimal("1200.00")

    # 6. Highest single expense = ₹3,500.00
    assert summary["highest_expense"] == Decimal("3500.00")

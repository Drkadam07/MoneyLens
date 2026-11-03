import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database.models.account import BankAccount
from app.database.models.planning import Budget, RecurringPayment
from app.database.models.transaction import (
    Category,
    CategoryType,
    Merchant,
    PaymentMethod,
    ReviewStatus,
    Transaction,
    TransactionKind,
)
from app.database.models.user import User, UserPreference
from app.database.session import AsyncSessionLocal


async def seed_database():
    print("🌱 Starting MoneyLens Synthetic Data Seeder...")
    async with AsyncSessionLocal() as db:
        # 1. Create or get Demo User
        email = "demo@moneylens.ai"
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                password_hash=hash_password("Password123!"),
                full_name="Dhanraj Sharma",
                is_active=True,
            )
            db.add(user)
            await db.flush()

            pref = UserPreference(
                user_id=user.id,
                currency="INR",
                timezone="Asia/Kolkata",
                language="en",
                week_start_day=1,
            )
            db.add(pref)
            print(f"Created demo user: {email} / Password123!")
        else:
            print(f"User {email} already exists.")

        # 2. Create Bank Accounts (HDFC & ICICI)
        res = await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
        accounts = res.scalars().all()

        if not accounts:
            hdfc = BankAccount(
                user_id=user.id,
                bank_name="HDFC Bank",
                account_label="Primary Salary Account",
                account_type="SAVINGS",
                masked_account_number="XX5678",
                currency="INR",
                is_active=True,
            )
            icici = BankAccount(
                user_id=user.id,
                bank_name="ICICI Bank",
                account_label="Digital & UPI Account",
                account_type="SAVINGS",
                masked_account_number="XX1234",
                currency="INR",
                is_active=True,
            )
            db.add_all([hdfc, icici])
            await db.flush()
            primary_acc = hdfc
            secondary_acc = icici
            print("Created bank accounts: HDFC Bank and ICICI Bank.")
        else:
            primary_acc = accounts[0]
            secondary_acc = accounts[1] if len(accounts) > 1 else accounts[0]

        # 3. Create Categories
        categories_to_seed = [
            ("Food & Dining", CategoryType.EXPENSE),
            ("Groceries", CategoryType.EXPENSE),
            ("Shopping", CategoryType.EXPENSE),
            ("Housing", CategoryType.EXPENSE),
            ("Utilities", CategoryType.EXPENSE),
            ("Transport", CategoryType.EXPENSE),
            ("Entertainment", CategoryType.EXPENSE),
            ("Healthcare", CategoryType.EXPENSE),
            ("Income", CategoryType.INCOME),
            ("Investments", CategoryType.EXPENSE),
            ("Transfers", CategoryType.TRANSFER),
        ]

        cat_map = {}
        for name, c_type in categories_to_seed:
            res = await db.execute(select(Category).where(Category.name == name))
            cat = res.scalar_one_or_none()
            if not cat:
                cat = Category(name=name, category_type=c_type, is_system=True)
                db.add(cat)
                await db.flush()
            cat_map[name] = cat

        # 4. Create Merchants
        merchants_data = [
            ("swiggy", "Swiggy", cat_map["Food & Dining"].id),
            ("zomato", "Zomato", cat_map["Food & Dining"].id),
            ("zepto", "Zepto", cat_map["Groceries"].id),
            ("blinkit", "Blinkit", cat_map["Groceries"].id),
            ("amazon", "Amazon", cat_map["Shopping"].id),
            ("flipkart", "Flipkart", cat_map["Shopping"].id),
            ("uber", "Uber", cat_map["Transport"].id),
            ("airtel", "Airtel", cat_map["Utilities"].id),
            ("tatapower", "Tata Power", cat_map["Utilities"].id),
            ("netflix", "Netflix", cat_map["Entertainment"].id),
            ("spotify", "Spotify", cat_map["Entertainment"].id),
            ("zerodha", "Zerodha", cat_map["Investments"].id),
        ]

        merchant_map = {}
        for norm, disp, cat_id in merchants_data:
            res = await db.execute(select(Merchant).where(Merchant.normalized_name == norm))
            m = res.scalar_one_or_none()
            if not m:
                m = Merchant(normalized_name=norm, display_name=disp, default_category_id=cat_id)
                db.add(m)
                await db.flush()
            merchant_map[norm] = m

        # 5. Populate 90 days of transactions (Aug, Sep, Oct 2026)
        tx_count = await db.execute(select(Transaction).where(Transaction.user_id == user.id))
        if not tx_count.scalars().first():
            print("Populating 90-day transaction history with realistic Indian UPI & banking activity...")
            transactions_to_add = []
            base_date = date(2026, 8, 1)

            for month_offset in range(3):
                # Monthly Salary on 1st of month
                sal_date = base_date + timedelta(days=month_offset * 31)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=primary_acc.id,
                        transaction_date=sal_date,
                        description_original="NEFT-ACME CORP-OCTOBER SALARY-SALARY CREDITED",
                        description_normalized="ACME Corp Salary",
                        debit_amount=Decimal("0.00"),
                        credit_amount=Decimal("125000.00"),
                        currency="INR",
                        balance_after=Decimal("145000.00"),
                        reference_number=f"NEFT{sal_date.strftime('%Y%m%d')}1234",
                        payment_method=PaymentMethod.NETBANKING,
                        transaction_kind=TransactionKind.INCOME,
                        category_id=cat_map["Income"].id,
                    )
                )

                # Rent payment on 3rd of month
                rent_date = sal_date + timedelta(days=2)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=primary_acc.id,
                        transaction_date=rent_date,
                        description_original="IMPS/P2A/RENT PAYMENT FOR APARTMENT 402/OCTOBER",
                        description_normalized="Apartment Rent",
                        debit_amount=Decimal("32000.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        balance_after=Decimal("113000.00"),
                        reference_number=f"IMPS{rent_date.strftime('%Y%m%d')}5678",
                        payment_method=PaymentMethod.NETBANKING,
                        transaction_kind=TransactionKind.EXPENSE,
                        category_id=cat_map["Housing"].id,
                    )
                )

                # Self transfer from Primary to Digital account on 4th
                transfer_date = sal_date + timedelta(days=3)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=primary_acc.id,
                        transaction_date=transfer_date,
                        description_original="TRANSFER TO OWN ICICI ACCOUNT XX1234",
                        description_normalized="Self-Transfer to ICICI",
                        debit_amount=Decimal("20000.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        balance_after=Decimal("93000.00"),
                        reference_number=f"TRF{transfer_date.strftime('%Y%m%d')}01",
                        payment_method=PaymentMethod.NETBANKING,
                        transaction_kind=TransactionKind.TRANSFER,
                        category_id=cat_map["Transfers"].id,
                    )
                )
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=secondary_acc.id,
                        transaction_date=transfer_date,
                        description_original="TRANSFER FROM HDFC ACCOUNT XX5678",
                        description_normalized="Self-Transfer from HDFC",
                        debit_amount=Decimal("0.00"),
                        credit_amount=Decimal("20000.00"),
                        currency="INR",
                        balance_after=Decimal("22500.00"),
                        reference_number=f"TRF{transfer_date.strftime('%Y%m%d')}01",
                        payment_method=PaymentMethod.NETBANKING,
                        transaction_kind=TransactionKind.TRANSFER,
                        category_id=cat_map["Transfers"].id,
                    )
                )

                # Investment SIP to Zerodha on 7th
                sip_date = sal_date + timedelta(days=6)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=primary_acc.id,
                        transaction_date=sip_date,
                        description_original="ACH D-ZERODHA BROKING LTD-MONTHLY SIP MUTUAL FUND",
                        description_normalized="Zerodha SIP",
                        debit_amount=Decimal("25000.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        balance_after=Decimal("68000.00"),
                        reference_number=f"ACH{sip_date.strftime('%Y%m%d')}99",
                        payment_method=PaymentMethod.NETBANKING,
                        transaction_kind=TransactionKind.INVESTMENT,
                        merchant_id=merchant_map["zerodha"].id,
                        category_id=cat_map["Investments"].id,
                    )
                )

                # Electricity and Broadband bills on 10th
                bill_date = sal_date + timedelta(days=9)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=secondary_acc.id,
                        transaction_date=bill_date,
                        description_original="UPI/DR/TATAPOWER/CONSUMER987654/ELECTRICITY BILL",
                        description_normalized="Tata Power",
                        debit_amount=Decimal("2450.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        reference_number=f"UPI{bill_date.strftime('%Y%m%d')}22",
                        payment_method=PaymentMethod.UPI,
                        transaction_kind=TransactionKind.EXPENSE,
                        merchant_id=merchant_map["tatapower"].id,
                        category_id=cat_map["Utilities"].id,
                    )
                )
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=secondary_acc.id,
                        transaction_date=bill_date,
                        description_original="UPI/DR/AIRTEL/BROADBAND FIBER RECHARGE",
                        description_normalized="Airtel",
                        debit_amount=Decimal("1179.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        reference_number=f"UPI{bill_date.strftime('%Y%m%d')}23",
                        payment_method=PaymentMethod.UPI,
                        transaction_kind=TransactionKind.EXPENSE,
                        merchant_id=merchant_map["airtel"].id,
                        category_id=cat_map["Utilities"].id,
                    )
                )

                # Netflix & Spotify Subscriptions on 15th
                sub_date = sal_date + timedelta(days=14)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=secondary_acc.id,
                        transaction_date=sub_date,
                        description_original="POS 453212XXXXXX1234 NETFLIX ENTERTAINMENT MUMBAI",
                        description_normalized="Netflix",
                        debit_amount=Decimal("649.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        reference_number=f"POS{sub_date.strftime('%Y%m%d')}01",
                        payment_method=PaymentMethod.CARD,
                        transaction_kind=TransactionKind.EXPENSE,
                        merchant_id=merchant_map["netflix"].id,
                        category_id=cat_map["Entertainment"].id,
                    )
                )
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=secondary_acc.id,
                        transaction_date=sub_date,
                        description_original="UPI/DR/SPOTIFY/PREMIUM INDIVIDUAL",
                        description_normalized="Spotify",
                        debit_amount=Decimal("119.00"),
                        credit_amount=Decimal("0.00"),
                        currency="INR",
                        reference_number=f"UPI{sub_date.strftime('%Y%m%d')}98",
                        payment_method=PaymentMethod.UPI,
                        transaction_kind=TransactionKind.EXPENSE,
                        merchant_id=merchant_map["spotify"].id,
                        category_id=cat_map["Entertainment"].id,
                    )
                )

                # Frequent UPI payments (Swiggy, Zomato, Zepto, Uber) throughout the month
                for day_step in range(1, 28, 2):
                    upi_date = sal_date + timedelta(days=day_step)
                    # Swiggy
                    transactions_to_add.append(
                        Transaction(
                            user_id=user.id,
                            account_id=secondary_acc.id,
                            transaction_date=upi_date,
                            description_original=f"UPI/DR/SWIGGY/ORDER_{day_step}891/PAYMENT",
                            description_normalized="Swiggy",
                            debit_amount=Decimal(str(320 + (day_step * 15) % 400)),
                            credit_amount=Decimal("0.00"),
                            currency="INR",
                            reference_number=f"UPI{upi_date.strftime('%Y%m%d')}{day_step}1",
                            payment_method=PaymentMethod.UPI,
                            transaction_kind=TransactionKind.EXPENSE,
                            merchant_id=merchant_map["swiggy"].id,
                            category_id=cat_map["Food & Dining"].id,
                        )
                    )
                    # Zepto Groceries
                    if day_step % 4 == 0:
                        transactions_to_add.append(
                            Transaction(
                                user_id=user.id,
                                account_id=secondary_acc.id,
                                transaction_date=upi_date,
                                description_original="UPI/DR/ZEPTO/QUICK GROCERIES ORDER",
                                description_normalized="Zepto",
                                debit_amount=Decimal("780.00"),
                                credit_amount=Decimal("0.00"),
                                currency="INR",
                                reference_number=f"UPI{upi_date.strftime('%Y%m%d')}{day_step}2",
                                payment_method=PaymentMethod.UPI,
                                transaction_kind=TransactionKind.EXPENSE,
                                merchant_id=merchant_map["zepto"].id,
                                category_id=cat_map["Groceries"].id,
                            )
                        )
                    # Uber Cab
                    if day_step % 5 == 0:
                        transactions_to_add.append(
                            Transaction(
                                user_id=user.id,
                                account_id=secondary_acc.id,
                                transaction_date=upi_date,
                                description_original="UPI/DR/UBER/TRIP RIDE PAYMENT",
                                description_normalized="Uber",
                                debit_amount=Decimal("450.00"),
                                credit_amount=Decimal("0.00"),
                                currency="INR",
                                reference_number=f"UPI{upi_date.strftime('%Y%m%d')}{day_step}3",
                                payment_method=PaymentMethod.UPI,
                                transaction_kind=TransactionKind.EXPENSE,
                                merchant_id=merchant_map["uber"].id,
                                category_id=cat_map["Transport"].id,
                            )
                        )

                # An Amazon Refund on 20th
                refund_date = sal_date + timedelta(days=19)
                transactions_to_add.append(
                    Transaction(
                        user_id=user.id,
                        account_id=primary_acc.id,
                        transaction_date=refund_date,
                        description_original="REFUND/AMAZON PAY RETAIL RETURN CREDIT",
                        description_normalized="Amazon Refund",
                        debit_amount=Decimal("0.00"),
                        credit_amount=Decimal("1899.00"),
                        currency="INR",
                        reference_number=f"REF{refund_date.strftime('%Y%m%d')}77",
                        payment_method=PaymentMethod.CARD,
                        transaction_kind=TransactionKind.REFUND,
                        merchant_id=merchant_map["amazon"].id,
                        category_id=cat_map["Shopping"].id,
                    )
                )

            db.add_all(transactions_to_add)
            await db.commit()
            print(f"Successfully seeded {len(transactions_to_add)} synthetic financial transactions!")

        # 6. Create Budgets
        res = await db.execute(select(Budget).where(Budget.user_id == user.id))
        if not res.scalars().first():
            b1 = Budget(
                user_id=user.id,
                category_id=cat_map["Food & Dining"].id,
                amount=Decimal("12000.00"),
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 31),
            )
            b2 = Budget(
                user_id=user.id,
                category_id=cat_map["Groceries"].id,
                amount=Decimal("8000.00"),
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 31),
            )
            b3 = Budget(
                user_id=user.id,
                category_id=cat_map["Transport"].id,
                amount=Decimal("5000.00"),
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 31),
            )
            db.add_all([b1, b2, b3])
            await db.commit()
            print("Created sample budgets for Food & Dining, Groceries, and Transport.")

        # 7. Create Recurring Payments
        res = await db.execute(select(RecurringPayment).where(RecurringPayment.user_id == user.id))
        if not res.scalars().first():
            r1 = RecurringPayment(
                user_id=user.id,
                merchant_id=merchant_map["netflix"].id,
                category_id=cat_map["Entertainment"].id,
                title="Netflix",
                expected_amount=Decimal("649.00"),
                frequency="MONTHLY",
                next_expected_date=date(2026, 11, 15),
                status="ACTIVE",
                confidence=0.98,
                user_confirmed=True,
            )
            r2 = RecurringPayment(
                user_id=user.id,
                merchant_id=merchant_map["spotify"].id,
                category_id=cat_map["Entertainment"].id,
                title="Spotify",
                expected_amount=Decimal("119.00"),
                frequency="MONTHLY",
                next_expected_date=date(2026, 11, 15),
                status="ACTIVE",
                confidence=0.95,
                user_confirmed=True,
            )
            db.add_all([r1, r2])
            await db.commit()
            print("Created recurring subscriptions (Netflix, Spotify).")

    print("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())

import re
from typing import Dict, Optional, Tuple


# Known common Indian merchants and patterns
KNOWN_MERCHANTS: Dict[str, str] = {
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "uber": "Uber",
    "ola": "Ola",
    "zepto": "Zepto",
    "blinkit": "Blinkit",
    "bigbasket": "BigBasket",
    "bbdaily": "BigBasket Daily",
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "myntra": "Myntra",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "hotstar": "Disney+ Hotstar",
    "airtel": "Airtel",
    "jio": "Jio",
    "tatapower": "Tata Power",
    "bescom": "BESCOM",
    "starbucks": "Starbucks",
    "mcdonald": "McDonald's",
    "dominos": "Domino's Pizza",
    "cultfit": "Cult.fit",
    "makemytrip": "MakeMyTrip",
    "irctc": "IRCTC",
    "bookmyshow": "BookMyShow",
    "cred": "CRED",
    "phonepe": "PhonePe",
    "googlepay": "Google Pay",
    "paytm": "Paytm",
    "zerodha": "Zerodha",
    "groww": "Groww",
    "upstox": "Upstox",
}


def clean_narration(narration: str) -> str:
    """Strip redundant whitespace, bank reference artifacts, and unwanted punctuation."""
    if not narration:
        return ""
    # Replace multiple spaces / newlines with single space
    cleaned = re.sub(r"\s+", " ", narration.strip())
    return cleaned


def detect_payment_method(narration: str) -> str:
    """Identify payment channel: UPI, CARD, NETBANKING, CASH, CHEQUE, or OTHER."""
    upper = narration.upper()
    if "UPI/" in upper or "UPI-" in upper or "/UPI" in upper or upper.startswith("UPI"):
        return "UPI"
    if any(k in upper for k in ["POS ", "POS/", "ECOM", "DEBIT CARD", "CREDIT CARD", "VISA", "MASTERCARD"]):
        return "CARD"
    if any(k in upper for k in ["NEFT", "RTGS", "IMPS", "INF/", "NETBANK"]):
        return "NETBANKING"
    if any(k in upper for k in ["ATM WDL", "ATM-WDL", "CASH WDL", "CASH DEPOSIT", "ATM CASH"]):
        return "CASH"
    if any(k in upper for k in ["CHQ", "CHEQUE", "CLG", "CLEARING"]):
        return "CHEQUE"
    return "OTHER"


def extract_merchant(narration: str) -> Optional[str]:
    """Extract cleaned merchant display name using tokenization and pattern matching."""
    cleaned = clean_narration(narration)
    lower = cleaned.lower()

    # 1. Match known merchant dictionaries
    for key, display_name in KNOWN_MERCHANTS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            return display_name

    # 2. Extract from standard UPI narration format: UPI/DR/MERCHANT/REF or UPI/MERCHANT@BANK/REF
    upi_match = re.search(r"UPI/(?:DR|CR)/([^/]+)", cleaned, re.IGNORECASE)
    if upi_match:
        token = upi_match.group(1).strip()
        # Remove trailing alphanumeric transaction tokens
        token = re.sub(r"[0-9_\-]+", " ", token).strip()
        if len(token) >= 2:
            return token.title()

    vpa_match = re.search(r"UPI/([a-zA-Z0-9.\-_]+)@[a-zA-Z0-9]+", cleaned, re.IGNORECASE)
    if vpa_match:
        vpa_user = vpa_match.group(1).replace(".", " ").replace("-", " ").strip()
        return vpa_user.title()

    # 3. Match POS format: POS 4532XXXXXXXX1234 MERCHANT_NAME LOCATION
    pos_match = re.search(r"POS\s+(?:[\dX]+)\s+([A-Za-z\s]+)", cleaned, re.IGNORECASE)
    if pos_match:
        return pos_match.group(1).strip().title()

    return None


def classify_transaction_kind(
    narration: str,
    debit_amount: float,
    credit_amount: float,
    merchant_name: Optional[str] = None
) -> str:
    """Classify the deterministic nature of transaction (Debit != Expense, Credit != Income)."""
    upper = narration.upper()

    # 1. Refunds
    if credit_amount > 0 and any(w in upper for w in ["REFUND", "REVERSAL", "CASHBACK", "RETURN"]):
        return "REFUND"

    # 2. Cash Withdrawals
    if debit_amount > 0 and any(w in upper for w in ["ATM WDL", "ATM CASH", "CASH WDL", "SELF CASH"]):
        return "CASH_WITHDRAWAL"

    # 3. Investments
    if any(w in upper for w in ["ZERODHA", "GROWW", "MUTUAL FUND", "MF INVEST", "KITE", "UPSTOX", "INDMONEY", "NSE", "BSE"]):
        return "INVESTMENT"

    # 4. Transfers (Self-transfer keywords or own account markings)
    if any(w in upper for w in ["OWN AC", "SELF TRANSFER", "TRF TO OWN", "INTER ACCOUNT", "TO SAVINGS", "TO CURRENT"]):
        return "TRANSFER"

    # 5. Salary / Payroll
    if credit_amount > 0 and any(w in upper for w in ["SALARY", "PAYROLL", "STIPEND", "WAGES"]):
        return "INCOME"

    # 6. Standard Debits vs Credits
    if debit_amount > 0:
        return "EXPENSE"
    elif credit_amount > 0:
        return "INCOME"

    return "UNCLASSIFIED"


def normalize_transaction_record(
    raw_date,
    raw_narration: str,
    debit: float,
    credit: float,
    balance: Optional[float] = None,
    ref: Optional[str] = None
) -> Dict[str, any]:
    """Full normalization pipeline for a single transaction row."""
    cleaned = clean_narration(raw_narration)
    method = detect_payment_method(cleaned)
    merchant = extract_merchant(cleaned)
    kind = classify_transaction_kind(cleaned, debit, credit, merchant)

    # Clean normalized description
    norm_desc = merchant if merchant else cleaned
    if len(norm_desc) > 200:
        norm_desc = norm_desc[:197] + "..."

    return {
        "transaction_date": raw_date,
        "description_original": raw_narration.strip(),
        "description_normalized": norm_desc,
        "debit_amount": debit,
        "credit_amount": credit,
        "balance_after": balance,
        "reference_number": ref.strip() if ref else None,
        "payment_method": method,
        "transaction_kind": kind,
        "merchant_guess": merchant,
    }

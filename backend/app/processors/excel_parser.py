from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from app.processors.base import BaseStatementParser
from app.processors.normalization import normalize_transaction_record


class ExcelStatementParser(BaseStatementParser):
    """Excel statement parser for .xlsx and .xls formats."""

    DATE_ALIASES = ["date", "txn_date", "txn date", "transaction date", "value date"]
    DESC_ALIASES = ["description", "narration", "particulars", "remarks", "details"]
    DEBIT_ALIASES = ["debit", "withdrawal", "dr", "debit amount", "withdrawal amount"]
    CREDIT_ALIASES = ["credit", "deposit", "cr", "credit amount", "deposit amount"]
    BALANCE_ALIASES = ["balance", "closing balance", "net balance"]
    REF_ALIASES = ["chq/ref no", "ref no", "cheque no", "reference number", "txn id"]

    def can_parse(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False
        return file_path.suffix.lower() in [".xlsx", ".xls"]

    def _clean_amount(self, val: Any) -> Decimal:
        if val is None or pd.isna(val):
            return Decimal("0.00")
        s = str(val).strip().replace(",", "").replace("₹", "").replace("$", "").replace("INR", "").strip()
        if not s or s.lower() == "nan" or s == "-":
            return Decimal("0.00")
        try:
            return abs(Decimal(s))
        except InvalidOperation:
            return Decimal("0.00")

    def _parse_date(self, val: Any) -> Optional[date]:
        if not val or pd.isna(val):
            return None
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return pd.to_datetime(str(val).strip(), dayfirst=True).date()
        except Exception:
            return None

    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        # Read the excel sheet into a DataFrame
        df = pd.read_excel(file_path, dtype=str)

        col_map = {}
        for col in df.columns:
            clean_col = str(col).strip().lower()
            if any(clean_col.startswith(a) for a in self.DATE_ALIASES):
                col_map["date"] = col
            elif any(clean_col.startswith(a) for a in self.DESC_ALIASES):
                col_map["desc"] = col
            elif any(clean_col.startswith(a) for a in self.DEBIT_ALIASES):
                col_map["debit"] = col
            elif any(clean_col.startswith(a) for a in self.CREDIT_ALIASES):
                col_map["credit"] = col
            elif any(clean_col.startswith(a) for a in self.BALANCE_ALIASES):
                col_map["balance"] = col
            elif any(clean_col.startswith(a) for a in self.REF_ALIASES):
                col_map["ref"] = col

        raw_rows = []
        for idx, row in df.iterrows():
            raw_date = row.get(col_map.get("date")) if "date" in col_map else None
            raw_desc = row.get(col_map.get("desc")) if "desc" in col_map else ""
            raw_debit = row.get(col_map.get("debit")) if "debit" in col_map else "0.00"
            raw_credit = row.get(col_map.get("credit")) if "credit" in col_map else "0.00"
            raw_bal = row.get(col_map.get("balance")) if "balance" in col_map else None
            raw_ref = row.get(col_map.get("ref")) if "ref" in col_map else None

            if not raw_date or (pd.isna(raw_desc) and pd.isna(raw_debit) and pd.isna(raw_credit)):
                continue

            raw_rows.append({
                "row_number": idx + 1,
                "raw_date": raw_date,
                "raw_narration": str(raw_desc) if not pd.isna(raw_desc) else "",
                "raw_debit": raw_debit,
                "raw_credit": raw_credit,
                "raw_balance": raw_bal,
                "raw_ref": str(raw_ref) if not pd.isna(raw_ref) else None,
            })
        return raw_rows

    def normalize(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for r in rows:
            parsed_date = self._parse_date(r.get("raw_date"))
            if not parsed_date:
                continue

            debit = self._clean_amount(r.get("raw_debit"))
            credit = self._clean_amount(r.get("raw_credit"))
            balance = self._clean_amount(r.get("raw_balance")) if r.get("raw_balance") is not None else None

            if debit == Decimal("0.00") and credit == Decimal("0.00"):
                continue

            norm_row = normalize_transaction_record(
                raw_date=parsed_date,
                raw_narration=r.get("raw_narration", ""),
                debit=float(debit),
                credit=float(credit),
                balance=float(balance) if balance is not None else None,
                ref=r.get("raw_ref"),
            )
            norm_row["row_number"] = r.get("row_number")
            normalized.append(norm_row)
        return normalized

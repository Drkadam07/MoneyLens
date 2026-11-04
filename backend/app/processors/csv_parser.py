import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.processors.base import BaseStatementParser
from app.processors.normalization import normalize_transaction_record


class CSVStatementParser(BaseStatementParser):
    """Robust CSV bank statement parser supporting varying column headers and date formats."""

    DATE_ALIASES = ["date", "txn_date", "txn date", "transaction date", "value date", "trans date"]
    DESC_ALIASES = ["description", "narration", "particulars", "remarks", "details", "transaction details"]
    DEBIT_ALIASES = ["debit", "withdrawal", "dr", "debit amount", "withdrawal amount", "withdrawals"]
    CREDIT_ALIASES = ["credit", "deposit", "cr", "credit amount", "deposit amount", "deposits"]
    BALANCE_ALIASES = ["balance", "closing balance", "net balance", "bal"]
    REF_ALIASES = ["chq/ref no", "ref no", "reference number", "cheque no", "chq no", "ref_no", "txn id", "reference"]

    def can_parse(self, file_path: Path) -> bool:
        if not file_path.exists() or file_path.suffix.lower() != ".csv":
            return False
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                first_lines = [f.readline() for _ in range(5)]
                content = "".join(first_lines).lower()
                has_date = any(alias in content for alias in self.DATE_ALIASES)
                has_money = any(alias in content for alias in self.DEBIT_ALIASES + self.CREDIT_ALIASES + self.BALANCE_ALIASES)
                return has_date and has_money
        except Exception:
            return False

    def _clean_amount(self, val: Any) -> Decimal:
        if val is None:
            return Decimal("0.00")
        s = str(val).strip().replace(",", "").replace("₹", "").replace("$", "").replace("INR", "").strip()
        if not s or s.lower() == "nan" or s == "-":
            return Decimal("0.00")
        if s.endswith("Dr") or s.endswith("dr"):
            s = s[:-2].strip()
        elif s.endswith("Cr") or s.endswith("cr"):
            s = s[:-2].strip()

        try:
            return abs(Decimal(s))
        except InvalidOperation:
            return Decimal("0.00")

    def _parse_date(self, val: Any) -> Optional[date]:
        if not val:
            return None
        s = str(val).strip()
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y",
            "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%Y/%m/%d"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        raw_rows = []
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            header = None
            header_map = {}

            for line_idx, row in enumerate(reader):
                if not row or not any(field.strip() for field in row):
                    continue

                clean_row = [c.strip().lower() for c in row]
                # Look for header row
                if not header and any(any(alias in c for alias in self.DATE_ALIASES) for c in clean_row):
                    header = row
                    for idx, c in enumerate(clean_row):
                        if any(c == a or c.startswith(a) for a in self.DATE_ALIASES):
                            header_map["date"] = idx
                        elif any(c == a or c.startswith(a) for a in self.DESC_ALIASES):
                            header_map["desc"] = idx
                        elif any(c == a for a in self.DEBIT_ALIASES):
                            header_map["debit"] = idx
                        elif any(c == a for a in self.CREDIT_ALIASES):
                            header_map["credit"] = idx
                        elif any(c == a for a in self.BALANCE_ALIASES):
                            header_map["balance"] = idx
                        elif any(c == a for a in self.REF_ALIASES):
                            header_map["ref"] = idx
                    continue

                if header and "date" in header_map:
                    date_idx = header_map["date"]
                    if date_idx < len(row):
                        raw_date = row[date_idx].strip()
                        raw_desc = row[header_map["desc"]].strip() if "desc" in header_map and header_map["desc"] < len(row) else ""
                        raw_debit = row[header_map["debit"]].strip() if "debit" in header_map and header_map["debit"] < len(row) else "0.00"
                        raw_credit = row[header_map["credit"]].strip() if "credit" in header_map and header_map["credit"] < len(row) else "0.00"
                        raw_bal = row[header_map["balance"]].strip() if "balance" in header_map and header_map["balance"] < len(row) else None
                        raw_ref = row[header_map["ref"]].strip() if "ref" in header_map and header_map["ref"] < len(row) else None

                        if raw_date:
                            raw_rows.append({
                                "row_number": line_idx + 1,
                                "raw_date": raw_date,
                                "raw_narration": raw_desc,
                                "raw_debit": raw_debit,
                                "raw_credit": raw_credit,
                                "raw_balance": raw_bal,
                                "raw_ref": raw_ref,
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

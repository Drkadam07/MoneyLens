import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.processors.base import BaseStatementParser
from app.processors.normalization import normalize_transaction_record


class PDFStatementParser(BaseStatementParser):
    """PDF bank statement parser utilizing pdfplumber and regex table extraction."""

    # Regex patterns for line matching
    DATE_REGEX = r"(\b\d{2}[/\-]\d{2}[/\-]\d{2,4}\b|\b\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b)"
    AMOUNT_REGEX = r"(\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b)"

    def can_parse(self, file_path: Path) -> bool:
        if not file_path.exists() or file_path.suffix.lower() != ".pdf":
            return False
        return True

    def _parse_date(self, date_str: str) -> Optional[date]:
        date_str = date_str.strip()
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
            "%d %b %Y", "%d %B %Y", "%Y-%m-%d"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _clean_amount(self, val: str) -> Decimal:
        if not val:
            return Decimal("0.00")
        s = val.replace(",", "").replace("₹", "").replace("$", "").strip()
        try:
            return abs(Decimal(s))
        except InvalidOperation:
            return Decimal("0.00")

    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        raw_rows = []
        row_counter = 1

        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # 1. Try table extraction first
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                if not row or len(row) < 3:
                                    continue
                                # Filter out header rows
                                row_str = " ".join([str(c) for c in row if c]).lower()
                                if "date" in row_str and ("balance" in row_str or "narration" in row_str or "withdrawal" in row_str):
                                    continue

                                # Check if first column has a date
                                first_col = str(row[0]).strip() if row[0] else ""
                                date_match = re.search(self.DATE_REGEX, first_col, re.IGNORECASE)
                                if date_match:
                                    raw_rows.append({
                                        "row_number": row_counter,
                                        "raw_date": date_match.group(1),
                                        "raw_narration": str(row[1]).strip() if len(row) > 1 and row[1] else "",
                                        "raw_ref": str(row[2]).strip() if len(row) > 2 and row[2] else "",
                                        "raw_debit": str(row[3]).strip() if len(row) > 3 and row[3] else "0.00",
                                        "raw_credit": str(row[4]).strip() if len(row) > 4 and row[4] else "0.00",
                                        "raw_balance": str(row[5]).strip() if len(row) > 5 and row[5] else None,
                                    })
                                    row_counter += 1

                    # 2. If table extraction yielded nothing, fallback to text regex line parsing
                    if not raw_rows:
                        text = page.extract_text() or ""
                        for line in text.split("\n"):
                            line = line.strip()
                            date_match = re.search(self.DATE_REGEX, line, re.IGNORECASE)
                            if not date_match:
                                continue

                            # Find all potential currency numbers in the line
                            amounts = re.findall(self.AMOUNT_REGEX, line)
                            if len(amounts) >= 2:
                                # Typically: [Debit/Credit, Balance] or [Debit, Credit, Balance]
                                date_str = date_match.group(1)
                                remainder = line[line.find(date_str) + len(date_str):].strip()

                                raw_rows.append({
                                    "row_number": row_counter,
                                    "raw_date": date_str,
                                    "raw_narration": remainder[:100],
                                    "raw_debit": amounts[0] if "DR" in line.upper() or "DEBIT" in line.upper() else "0.00",
                                    "raw_credit": amounts[0] if "CR" in line.upper() or "CREDIT" in line.upper() else "0.00",
                                    "raw_balance": amounts[-1] if len(amounts) >= 2 else None,
                                    "raw_ref": None,
                                })
                                row_counter += 1
        except Exception:
            # Fallback if pdfplumber fails or is not installed
            pass

        return raw_rows

    def normalize(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for r in rows:
            parsed_date = self._parse_date(str(r.get("raw_date", "")))
            if not parsed_date:
                continue

            debit = self._clean_amount(str(r.get("raw_debit", "0.00")))
            credit = self._clean_amount(str(r.get("raw_credit", "0.00")))
            balance = self._clean_amount(str(r.get("raw_balance", ""))) if r.get("raw_balance") else None

            if debit == Decimal("0.00") and credit == Decimal("0.00"):
                continue

            norm_row = normalize_transaction_record(
                raw_date=parsed_date,
                raw_narration=str(r.get("raw_narration", "")),
                debit=float(debit),
                credit=float(credit),
                balance=float(balance) if balance is not None else None,
                ref=r.get("raw_ref"),
            )
            norm_row["row_number"] = r.get("row_number")
            normalized.append(norm_row)
        return normalized

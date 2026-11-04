from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class BaseStatementParser(ABC):
    """Abstract base class defining contract for all bank statement parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Evaluate if the parser can interpret the given file format and content."""
        pass

    @abstractmethod
    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract raw records from the statement file."""
        pass

    @abstractmethod
    def normalize(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize extracted bank-specific rows into the unified MoneyLens transaction schema:
        {
            'transaction_date': date,
            'description_original': str,
            'description_normalized': str,
            'debit_amount': Decimal,
            'credit_amount': Decimal,
            'balance_after': Optional[Decimal],
            'reference_number': Optional[str],
            'payment_method': str,
            'transaction_kind': str,
            'merchant_guess': Optional[str]
        }
        """
        pass

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from app.database.models.statement import (
    Statement,
    StatementImportJob,
    StatementImportWarning,
    StatementRow,
    StatementStatus,
)
from app.database.session import get_sync_db
from app.processors.csv_parser import CSVStatementParser
from app.processors.excel_parser import ExcelStatementParser
from app.processors.pdf_parser import PDFStatementParser
from app.processors.validation import StatementValidator
from app.workers.celery_app import celery


@celery.task(name="tasks.process_statement_task")
def process_statement_task(statement_id_str: str, file_path_str: str) -> dict:
    """Extract and stage a statement outside the API request process."""
    db = get_sync_db()
    statement_id = uuid.UUID(statement_id_str)
    try:
        statement = db.query(Statement).filter(Statement.id == statement_id).first()
        job = db.query(StatementImportJob).filter(
            StatementImportJob.statement_id == statement_id
        ).first()
        if not statement or not job:
            return {"status": "FAILED", "error": "Statement import record not found"}

        job.status = StatementStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        statement.status = StatementStatus.PROCESSING
        db.commit()

        file_path = Path(file_path_str)
        ext = file_path.suffix.lower()
        parser = (
            CSVStatementParser() if ext == ".csv" else
            ExcelStatementParser() if ext in (".xlsx", ".xls") else
            PDFStatementParser() if ext == ".pdf" else None
        )
        if parser is None:
            raise ValueError(f"Unsupported format {ext}")

        rows = parser.normalize(parser.extract(file_path))
        job.total_rows = len(rows)
        if not rows:
            raise ValueError("Could not extract any valid financial rows from file.")

        statement.status = StatementStatus.VALIDATING
        job.status = StatementStatus.VALIDATING
        valid, warnings = StatementValidator.validate_statement_records(rows)
        for warning in warnings:
            db.add(StatementImportWarning(
                statement_id=statement.id,
                row_number=warning["row_number"],
                warning_type=warning["warning_type"],
                message=warning["message"],
            ))

        dates = [r["transaction_date"] for r in rows if r.get("transaction_date")]
        if dates:
            statement.period_start, statement.period_end = min(dates), max(dates)
        if rows[0].get("balance_after") is not None:
            statement.opening_balance = rows[0]["balance_after"]
        if rows[-1].get("balance_after") is not None:
            statement.closing_balance = rows[-1]["balance_after"]

        for row in rows:
            payload = {
                key: value.isoformat() if isinstance(value, (date, datetime)) else value
                for key, value in row.items()
            }
            db.add(StatementRow(
                statement_id=statement.id,
                row_number=row.get("row_number", 0),
                raw_payload=payload,
                parse_status="VALIDATED",
            ))

        job.processed_rows = len(rows)
        job.status = StatementStatus.REVIEW_REQUIRED
        job.completed_at = datetime.now(timezone.utc)
        statement.status = StatementStatus.REVIEW_REQUIRED
        db.commit()
        return {"status": "SUCCESS", "statement_id": statement_id_str, "extracted_count": len(rows)}
    except Exception as exc:
        db.rollback()
        statement = db.query(Statement).filter(Statement.id == statement_id).first()
        job = db.query(StatementImportJob).filter(
            StatementImportJob.statement_id == statement_id
        ).first()
        if statement:
            statement.status = StatementStatus.FAILED
        if job:
            job.status = StatementStatus.FAILED
            job.error_code = "EXTRACTION_FAILURE"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "FAILED", "error": str(exc)}
    finally:
        db.close()

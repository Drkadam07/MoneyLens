import uuid
from pathlib import Path
from app.workers.celery_app import celery
from app.database.session import get_sync_db
from app.database.models.statement import Statement, StatementImportJob, StatementStatus
from app.processors.csv_parser import CSVStatementParser
from app.processors.excel_parser import ExcelStatementParser
from app.processors.pdf_parser import PDFStatementParser
from app.processors.validation import StatementValidator


@celery.task(name="tasks.process_statement_task")
def process_statement_task(statement_id_str: str, file_path_str: str) -> dict:
    """Asynchronous background worker task for statement ingestion and validation."""
    db = get_sync_db()
    stmt_uuid = uuid.UUID(statement_id_str)
    file_path = Path(file_path_str)

    try:
        statement = db.query(Statement).filter(Statement.id == stmt_uuid).first()
        if not statement:
            return {"status": "FAILED", "error": "Statement record not found"}

        job = db.query(StatementImportJob).filter(StatementImportJob.statement_id == stmt_uuid).first()

        # Parse file
        parser = None
        ext = file_path.suffix.lower()
        if ext == ".csv":
            parser = CSVStatementParser()
        elif ext in [".xlsx", ".xls"]:
            parser = ExcelStatementParser()
        elif ext == ".pdf":
            parser = PDFStatementParser()

        if not parser:
            statement.status = StatementStatus.FAILED
            if job:
                job.status = StatementStatus.FAILED
                job.error_message = f"Unsupported format {ext}"
            db.commit()
            return {"status": "FAILED", "error": "Unsupported parser format"}

        raw_rows = parser.extract(file_path)
        normalized = parser.normalize(raw_rows)

        if job:
            job.total_rows = len(normalized)
            job.processed_rows = len(normalized)
            job.status = StatementStatus.REVIEW_REQUIRED

        statement.status = StatementStatus.REVIEW_REQUIRED
        db.commit()

        return {
            "status": "SUCCESS",
            "statement_id": statement_id_str,
            "extracted_count": len(normalized),
        }
    except Exception as exc:
        db.rollback()
        return {"status": "FAILED", "error": str(exc)}
    finally:
        db.close()

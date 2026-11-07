# backend/app/modules/statements/service.py
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
from app.database.models import statement

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    FileTooLargeError,
    NotFoundError,
    StatementValidationError,
    UnsupportedStatementFormatError,
)
from app.database.models.account import BankAccount
from app.database.models.statement import (
    Statement,
    StatementImportJob,
    StatementImportWarning,
    StatementRow,
    StatementStatus,
)
from app.database.models.transaction import (
    Merchant,
    PaymentMethod,
    ReviewStatus,
    Transaction,
    TransactionKind,
)
from app.processors.csv_parser import CSVStatementParser
from app.processors.deduplication import TransactionDeduplicator
from app.processors.excel_parser import ExcelStatementParser
from app.processors.pdf_parser import PDFStatementParser
from app.processors.validation import StatementValidator


class StatementService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def _verify_account_ownership(self, account_id: uuid.UUID) -> BankAccount:
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.user_id == self.user_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError(
                f"Bank account '{account_id}' not found or access denied"
            )
        return account

    async def upload_statement(
        self,
        account_id: uuid.UUID,
        file: UploadFile,
    ) -> tuple[Statement, uuid.UUID]:
        # 1. Verify account ownership
        await self._verify_account_ownership(account_id)

        # 2. Read and validate content size
        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise FileTooLargeError(
                f"File size exceeds maximum {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # 3. Compute SHA-256 for idempotency
        file_hash = StatementValidator.compute_sha256(content)
        existing_stmt = await self.db.execute(
            select(Statement).where(
                Statement.account_id == account_id,
                Statement.file_hash == file_hash,
            )
        )
        previous_statement = existing_stmt.scalar_one_or_none()
        if previous_statement and previous_statement.status != StatementStatus.FAILED:
            raise ConflictError(
                "This statement has already been uploaded for this account (identical file hash)"
            )

        # 4. Save file to disk
        file_ext = Path(file.filename or "statement.pdf").suffix.lower()
        if file_ext not in [".csv", ".xlsx", ".xls", ".pdf"]:
            raise UnsupportedStatementFormatError(
                f"Unsupported file format '{file_ext}'. Allowed: .csv, .xlsx, .pdf"
            )

        upload_path = Path(settings.UPLOAD_DIR)
        upload_path.mkdir(parents=True, exist_ok=True)
        file_dest = (
            Path(previous_statement.storage_key)
            if previous_statement
            else upload_path / f"{uuid.uuid4()}{file_ext}"
        )
        with open(file_dest, "wb") as f:
            f.write(content)

        # 5. Create a new import or reset a failed one for retry.
        if previous_statement:
            statement = previous_statement
            job_result = await self.db.execute(
                select(StatementImportJob).where(
                    StatementImportJob.statement_id == statement.id,
                    StatementImportJob.user_id == self.user_id,
                )
            )
            job = job_result.scalar_one_or_none()
            if not job:
                raise ConflictError("Failed import has no job record and cannot be retried")
            await self.db.execute(delete(StatementRow).where(StatementRow.statement_id == statement.id))
            await self.db.execute(delete(StatementImportWarning).where(StatementImportWarning.statement_id == statement.id))
            statement.original_filename = file.filename or statement.original_filename
            statement.file_type = file_ext.replace(".", "")
            statement.storage_key = str(file_dest)
            statement.status = StatementStatus.PROCESSING
            statement.period_start = statement.period_end = None
            statement.opening_balance = statement.closing_balance = None
            job.status = StatementStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.completed_at = None
            job.error_code = job.error_message = None
            job.total_rows = job.processed_rows = 0
        else:
            statement = Statement(
                user_id=self.user_id,
                account_id=account_id,
                storage_key=str(file_dest),
                original_filename=file.filename or "statement",
                file_type=file_ext.replace(".", ""),
                file_hash=file_hash,
                status=StatementStatus.PROCESSING,
            )
            self.db.add(statement)
            await self.db.flush()

            job = StatementImportJob(
                statement_id=statement.id,
                user_id=self.user_id,
                status=StatementStatus.PROCESSING,
                started_at=datetime.now(timezone.utc),
            )
            self.db.add(job)

        # Persist the job and obtain its ID.
        await self.db.flush()
        job_id = job.id

        await self.db.commit()

        # Extraction is CPU and I/O heavy, especially for PDFs. Queue it so the
        # upload request can return immediately and the API event loop stays free.
        from app.workers.statement_tasks import process_statement_task
        try:
            process_statement_task.delay(str(statement.id), str(file_dest))
        except Exception as exc:
            job.status = StatementStatus.FAILED
            job.error_code = "QUEUE_FAILURE"
            job.error_message = f"Could not queue statement extraction: {exc}"
            statement.status = StatementStatus.FAILED
            await self.db.commit()

        return statement, job_id

    async def get_job_status(self, job_id: uuid.UUID) -> StatementImportJob:
        result = await self.db.execute(
            select(StatementImportJob).where(
                StatementImportJob.id == job_id,
                StatementImportJob.user_id == self.user_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError(f"Import job '{job_id}' not found")
        return job

    async def retry_statement(self, statement_id: uuid.UUID) -> StatementImportJob:
        result = await self.db.execute(
            select(Statement).where(
                Statement.id == statement_id,
                Statement.user_id == self.user_id,
            )
        )
        statement = result.scalar_one_or_none()
        if not statement:
            raise NotFoundError(f"Statement '{statement_id}' not found")

        result = await self.db.execute(
            select(StatementImportJob).where(
                StatementImportJob.statement_id == statement_id,
                StatementImportJob.user_id == self.user_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("Statement import job not found")
        if statement.status in (StatementStatus.CONFIRMED, StatementStatus.REVIEW_REQUIRED):
            raise ConflictError("This statement is already ready for review or has been imported")
        if job.status == StatementStatus.PROCESSING and job.started_at:
            started_at = job.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - started_at < timedelta(minutes=5):
                raise ConflictError("Extraction is still recent. Wait five minutes before retrying.")

        file_path = Path(statement.storage_key)
        if not file_path.exists():
            raise StatementValidationError("The uploaded statement file is missing from storage")

        await self.db.execute(delete(StatementRow).where(StatementRow.statement_id == statement.id))
        await self.db.execute(delete(StatementImportWarning).where(StatementImportWarning.statement_id == statement.id))
        statement.status = job.status = StatementStatus.PROCESSING
        statement.period_start = statement.period_end = None
        statement.opening_balance = statement.closing_balance = None
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = None
        job.error_code = job.error_message = None
        job.total_rows = job.processed_rows = 0
        await self.db.commit()

        from app.workers.statement_tasks import process_statement_task
        try:
            process_statement_task.delay(str(statement.id), str(file_path))
        except Exception as exc:
            statement.status = job.status = StatementStatus.FAILED
            job.error_code = "QUEUE_FAILURE"
            job.error_message = f"Could not queue statement extraction: {exc}"
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
        return job

    async def _process_statement_internal(
        self, statement: Statement, job: StatementImportJob, file_path: Path
    ) -> None:
        """Parse raw file, validate records, and store staging rows with warnings."""
        try:
            parser = None
            if file_path.suffix.lower() == ".csv":
                parser = CSVStatementParser()
            elif file_path.suffix.lower() in [".xlsx", ".xls"]:
                parser = ExcelStatementParser()
            elif file_path.suffix.lower() == ".pdf":
                parser = PDFStatementParser()

            if not parser:
                raise UnsupportedStatementFormatError(
                    f"No parser available for {file_path.suffix}"
                )

            raw_extracted = parser.extract(file_path)
            normalized_records = parser.normalize(raw_extracted)

            job.total_rows = len(normalized_records)

            if not normalized_records:
                statement.status = StatementStatus.FAILED
                job.status = StatementStatus.FAILED
                job.error_code = "NO_RECORDS_EXTRACTED"
                job.error_message = (
                    "Could not extract any valid financial rows from file."
                )
                job.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                return

            # Statement Validation
            statement.status = StatementStatus.VALIDATING
            is_valid, validation_warnings = (
                StatementValidator.validate_statement_records(normalized_records)
            )

            for w in validation_warnings:
                warning_rec = StatementImportWarning(
                    statement_id=statement.id,
                    row_number=w["row_number"],
                    warning_type=w["warning_type"],
                    message=w["message"],
                )
                self.db.add(warning_rec)

            # Store rows in statement_rows staging table
            dates = [
                r["transaction_date"]
                for r in normalized_records
                if r.get("transaction_date")
            ]
            if dates:
                statement.period_start = min(dates)
                statement.period_end = max(dates)

            first_balance = normalized_records[0].get("balance_after")
            last_balance = normalized_records[-1].get("balance_after")
            if first_balance is not None:
                statement.opening_balance = Decimal(str(first_balance))
            if last_balance is not None:
                statement.closing_balance = Decimal(str(last_balance))

            for r in normalized_records:
                st_row = StatementRow(
                    statement_id=statement.id,
                    row_number=r.get("row_number", 0),
                    raw_payload={
                        k: (str(v) if isinstance(v, (Decimal, datetime)) else v)
                        for k, v in r.items()
                    },
                    parse_status="VALIDATED",
                )
                self.db.add(st_row)

            job.processed_rows = len(normalized_records)
            job.status = StatementStatus.REVIEW_REQUIRED
            job.completed_at = datetime.now(timezone.utc)
            statement.status = StatementStatus.REVIEW_REQUIRED

            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            statement.status = StatementStatus.FAILED
            job.status = StatementStatus.FAILED
            job.error_code = "EXTRACTION_FAILURE"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            self.db.add(statement)
            self.db.add(job)
            await self.db.commit()

    async def get_preview(self, statement_id: uuid.UUID) -> Dict[str, Any]:
        """Fetch extracted statement staging rows, warnings, and deduplication scores."""
        stmt = (
            select(Statement)
            .options(
                selectinload(Statement.rows),
                selectinload(Statement.warnings),
            )
            .where(
                Statement.id == statement_id,
                Statement.user_id == self.user_id,
            )
        )
        res = await self.db.execute(stmt)
        statement = res.scalar_one_or_none()
        if not statement:
            raise NotFoundError(f"Statement '{statement_id}' not found")

        # Convert rows into dictionary list
        parsed_rows = [row.raw_payload for row in statement.rows]

        # Deduplication check against existing transactions
        deduplicator = TransactionDeduplicator(
            self.db, self.user_id, statement.account_id
        )
        dedup_results = await deduplicator.detect_duplicates(parsed_rows)

        preview_rows = []
        for cand, matched_existing, confidence in dedup_results:
            preview_rows.append(
                {
                    "row_number": cand.get("row_number", 0),
                    "transaction_date": cand.get("transaction_date"),
                    "description_original": cand.get("description_original", ""),
                    "description_normalized": cand.get("description_normalized", ""),
                    "debit_amount": Decimal(str(cand.get("debit_amount", 0))),
                    "credit_amount": Decimal(str(cand.get("credit_amount", 0))),
                    "balance_after": (
                        Decimal(str(cand["balance_after"]))
                        if cand.get("balance_after") is not None
                        else None
                    ),
                    "reference_number": cand.get("reference_number"),
                    "payment_method": cand.get("payment_method", "OTHER"),
                    "transaction_kind": cand.get("transaction_kind", "UNCLASSIFIED"),
                    "merchant_guess": cand.get("merchant_guess"),
                    "is_duplicate_candidate": confidence >= 0.85,
                    "duplicate_confidence": confidence,
                    "duplicate_match_details": matched_existing,
                }
            )

        return {
            "statement_id": statement.id,
            "status": statement.status,
            "total_records": len(preview_rows),
            "rows": preview_rows,
            "warnings": statement.warnings,
        }

    async def confirm_statement(
        self, statement_id: uuid.UUID, confirmed_rows: Optional[List[int]] = None
    ) -> int:
        """Promote staging records into the primary transactions ledger."""
        stmt = (
            select(Statement)
            .options(selectinload(Statement.rows))
            .where(
                Statement.id == statement_id,
                Statement.user_id == self.user_id,
            )
        )
        res = await self.db.execute(stmt)
        statement = res.scalar_one_or_none()
        if not statement:
            raise NotFoundError(f"Statement '{statement_id}' not found")

        if statement.status == StatementStatus.CONFIRMED:
            raise ConflictError("Statement has already been confirmed and imported")

        imported_count = 0
        for row in statement.rows:
            payload = row.raw_payload
            row_num = row.row_number
            if confirmed_rows is not None and row_num not in confirmed_rows:
                continue

            # Link or create merchant
            merchant_guess = payload.get("merchant_guess")
            merchant_id = None
            if merchant_guess:
                m_res = await self.db.execute(
                    select(Merchant).where(
                        Merchant.normalized_name == merchant_guess.lower()
                    )
                )
                merchant = m_res.scalar_one_or_none()
                if not merchant:
                    merchant = Merchant(
                        normalized_name=merchant_guess.lower(),
                        display_name=merchant_guess,
                    )
                    self.db.add(merchant)
                    await self.db.flush()
                merchant_id = merchant.id

            tx_date_str = payload.get("transaction_date")
            tx_date = (
                datetime.strptime(tx_date_str, "%Y-%m-%d").date()
                if tx_date_str
                else datetime.now(timezone.utc).date()
            )

            # Method & Kind mapping
            try:
                method_enum = PaymentMethod(payload.get("payment_method", "OTHER"))
            except ValueError:
                method_enum = PaymentMethod.OTHER

            try:
                kind_enum = TransactionKind(
                    payload.get("transaction_kind", "UNCLASSIFIED")
                )
            except ValueError:
                kind_enum = TransactionKind.UNCLASSIFIED

            tx = Transaction(
                user_id=self.user_id,
                account_id=statement.account_id,
                statement_id=statement.id,
                merchant_id=merchant_id,
                transaction_date=tx_date,
                description_original=payload.get("description_original", ""),
                description_normalized=payload.get("description_normalized", ""),
                debit_amount=Decimal(str(payload.get("debit_amount", 0))),
                credit_amount=Decimal(str(payload.get("credit_amount", 0))),
                currency="INR",
                balance_after=(
                    Decimal(str(payload["balance_after"]))
                    if payload.get("balance_after") is not None
                    else None
                ),
                reference_number=payload.get("reference_number"),
                payment_method=method_enum,
                transaction_kind=kind_enum,
                review_status=ReviewStatus.CONFIRMED,
            )
            self.db.add(tx)
            row.transaction_id = tx.id
            imported_count += 1

        statement.status = StatementStatus.CONFIRMED
        await self.db.commit()
        return imported_count

    # async def list_statements(self) -> List[Statement]:
    #     res = await self.db.execute(
    #         select(Statement)
    #         .where(Statement.user_id == self.user_id)
    #         .order_by(Statement.created_at.desc())
    #     )
    #     return res.scalars().all()

    async def list_statements(self) -> List[Statement]:
        res = await self.db.execute(
            select(Statement)
            .options(selectinload(Statement.warnings))
            .where(Statement.user_id == self.user_id)
            .order_by(Statement.created_at.desc())
        )

        return res.scalars().all()

    # async def get_statement(self, statement_id: uuid.UUID) -> Statement:
    #     res = await self.db.execute(
    #         select(Statement).where(
    #             Statement.id == statement_id,
    #             Statement.user_id == self.user_id,
    #         )
    #     )
    #     stmt = res.scalar_one_or_none()
    #     if not stmt:
    #         raise NotFoundError(f"Statement '{statement_id}' not found")
    #     return stmt

    async def get_statement(
        self,
        statement_id: uuid.UUID,
    ) -> Statement:

        res = await self.db.execute(
            select(Statement)
            .options(selectinload(Statement.warnings))
            .where(
                Statement.id == statement_id,
                Statement.user_id == self.user_id,
            )
        )

        stmt = res.scalar_one_or_none()

        if not stmt:
            raise NotFoundError(f"Statement '{statement_id}' not found")

        return stmt

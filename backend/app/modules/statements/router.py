# backend/app/modules/statements/router.py
import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.statements.schemas import (
    StatementConfirmRequest,
    StatementJobStatusResponse,
    StatementPreviewResponse,
    StatementResponse,
    StatementUploadResponse,
)
from app.modules.statements.service import StatementService

router = APIRouter(prefix="/statements", tags=["Statements"])


@router.post(
    "/upload",
    response_model=StatementUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_statement(
    account_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = StatementService(db, current_user.id)

    statement, job_id = await service.upload_statement(
        account_id,
        file,
    )

    return StatementUploadResponse(
        statement_id=statement.id,
        job_id=job_id,
        status=statement.status,
        message="Statement uploaded and validated. Review preview records.",
    )


@router.get("", response_model=List[StatementResponse])
async def list_statements(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = StatementService(db, current_user.id)
    statements = await service.list_statements()
    return [
        StatementResponse(
            id=s.id,
            account_id=s.account_id,
            original_filename=s.original_filename,
            file_type=s.file_type,
            period_start=s.period_start,
            period_end=s.period_end,
            opening_balance=s.opening_balance,
            closing_balance=s.closing_balance,
            status=s.status,
            created_at=s.created_at,
            warnings_count=len(s.warnings) if s.warnings else 0,
        )
        for s in statements
    ]


@router.get("/{statement_id}/preview", response_model=StatementPreviewResponse)
async def get_statement_preview(
    statement_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = StatementService(db, current_user.id)
    return await service.get_preview(statement_id)


@router.post("/{statement_id}/confirm", status_code=status.HTTP_200_OK)
async def confirm_statement_import(
    statement_id: uuid.UUID,
    request: StatementConfirmRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = StatementService(db, current_user.id)
    count = await service.confirm_statement(statement_id, request.confirmed_row_numbers)
    return {
        "message": f"Successfully imported and confirmed {count} transactions.",
        "imported_count": count,
    }


@router.get("/{statement_id}", response_model=StatementResponse)
async def get_statement(
    statement_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = StatementService(db, current_user.id)
    s = await service.get_statement(statement_id)
    return StatementResponse(
        id=s.id,
        account_id=s.account_id,
        original_filename=s.original_filename,
        file_type=s.file_type,
        period_start=s.period_start,
        period_end=s.period_end,
        opening_balance=s.opening_balance,
        closing_balance=s.closing_balance,
        status=s.status,
        created_at=s.created_at,
        warnings_count=len(s.warnings) if s.warnings else 0,
    )

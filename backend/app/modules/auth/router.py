from typing import Annotated
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_active_user
from app.database.models.user import User
from app.database.session import get_db
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    device_info = request.headers.get("user-agent", "unknown")
    return await service.login(data, device_info=device_info)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    return await service.refresh_tokens(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    await service.logout(data.refresh_token)
    return {"message": "Successfully logged out and session revoked"}


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    return await service.get_profile(current_user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    return await service.update_profile(current_user, data)

from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_sha256,
    verify_password,
)
from app.database.models.user import AuthSession, User, UserPreference
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> TokenResponse:
        # Check if user already exists
        existing = await self.db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise ConflictError(f"User with email '{data.email}' already exists")

        # Create user
        hashed = hash_password(data.password)
        user = User(
            email=data.email.lower(),
            password_hash=hashed,
            full_name=data.full_name,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        # Create default preferences
        preference = UserPreference(
            user_id=user.id,
            currency="INR",
            timezone="Asia/Kolkata",
            language="en",
            week_start_day=1,
        )
        self.db.add(preference)

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Record AuthSession
        refresh_hash = hash_sha256(refresh_token)
        session_record = AuthSession(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(session_record)
        await self.db.commit()
        await self.db.refresh(user)

        user_profile = UserProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            currency=preference.currency,
            timezone=preference.timezone,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_profile,
        )

    async def login(self, data: LoginRequest, device_info: Optional[str] = None) -> TokenResponse:
        result = await self.db.execute(
            select(User).options(selectinload(User.preference)).where(User.email == data.email.lower())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is inactive. Please contact support.")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        refresh_hash = hash_sha256(refresh_token)
        session_record = AuthSession(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            device_info=device_info,
        )
        self.db.add(session_record)
        await self.db.commit()

        curr = user.preference.currency if user.preference else "INR"
        tz = user.preference.timezone if user.preference else "Asia/Kolkata"

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserProfileResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                currency=curr,
                timezone=tz,
                created_at=user.created_at,
            ),
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id_str = payload.get("sub")
        refresh_hash = hash_sha256(refresh_token)

        # Verify active session in DB
        result = await self.db.execute(
            select(AuthSession).where(
                AuthSession.refresh_token_hash == refresh_hash,
                AuthSession.revoked_at.is_(None),
            )
        )
        session_record = result.scalar_one_or_none()
        if not session_record or session_record.expires_at < datetime.now(timezone.utc):
            raise AuthenticationError("Refresh token is invalid or has expired")

        # Load user
        user_res = await self.db.execute(
            select(User).options(selectinload(User.preference)).where(User.id == session_record.user_id)
        )
        user = user_res.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("User is inactive or not found")

        # Revoke previous session and issue new tokens
        session_record.revoked_at = datetime.now(timezone.utc)

        new_access_token = create_access_token(str(user.id))
        new_refresh_token = create_refresh_token(str(user.id))
        new_refresh_hash = hash_sha256(new_refresh_token)

        new_session = AuthSession(
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(new_session)
        await self.db.commit()

        curr = user.preference.currency if user.preference else "INR"
        tz = user.preference.timezone if user.preference else "Asia/Kolkata"

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            user=UserProfileResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                currency=curr,
                timezone=tz,
                created_at=user.created_at,
            ),
        )

    async def logout(self, refresh_token: str) -> None:
        refresh_hash = hash_sha256(refresh_token)
        result = await self.db.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == refresh_hash)
        )
        session_record = result.scalar_one_or_none()
        if session_record:
            session_record.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def get_profile(self, user: User) -> UserProfileResponse:
        res = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user.id)
        )
        pref = res.scalar_one_or_none()
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            currency=pref.currency if pref else "INR",
            timezone=pref.timezone if pref else "Asia/Kolkata",
            created_at=user.created_at,
        )

    async def update_profile(self, user: User, data: UpdateProfileRequest) -> UserProfileResponse:
        if data.full_name is not None:
            user.full_name = data.full_name

        res = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user.id)
        )
        pref = res.scalar_one_or_none()
        if not pref:
            pref = UserPreference(user_id=user.id)
            self.db.add(pref)

        if data.currency is not None:
            pref.currency = data.currency
        if data.timezone is not None:
            pref.timezone = data.timezone

        await self.db.commit()
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            currency=pref.currency,
            timezone=pref.timezone,
            created_at=user.created_at,
        )


from collections.abc import AsyncGenerator, Generator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.db import engine, async_session_maker
from app.models import TokenPayload, User


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


# ==========================================
# 同步数据库依赖：迁移期间暂时保留
# ==========================================

def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


# ==========================================
# 异步数据库依赖：新模块逐步使用
# ==========================================

async def get_async_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_db)]


TokenDep = Annotated[str, Depends(reusable_oauth2)]


# ==========================================
# 同步用户认证：迁移期间暂时保留
# ==========================================

def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if not token_data.sub:
            raise ValueError("Missing user ID in token")

        user_id = UUID(token_data.sub)

    except (InvalidTokenError, ValidationError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = session.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ==========================================
# 异步用户认证：异步路由使用
# ==========================================

async def get_current_user_async(
    session: AsyncSessionDep,
    token: TokenDep,
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if not token_data.sub:
            raise ValueError("Missing user ID in token")

        user_id = UUID(token_data.sub)

    except (InvalidTokenError, ValidationError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


CurrentUserAsync = Annotated[User, Depends(get_current_user_async)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


async def get_current_active_superuser_async(
    current_user: CurrentUserAsync,
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import Session, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud
from app.core.config import settings
from app.models import User, UserCreate


# ==========================================
# 同步数据库连接：迁移期间暂时保留
# ==========================================

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
)


# ==========================================
# 异步数据库连接：新模块逐步使用
# ==========================================

async_engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def init_db(session: Session) -> None:
    """初始化数据库基础数据，暂时保留同步实现。"""

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()

    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        crud.create_user(session=session, user_create=user_in)

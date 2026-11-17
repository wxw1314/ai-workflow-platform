
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import settings
from app.models import User, UserCreate
from app import crud


database_url = str(settings.DATABASE_URL)

connect_args = (
    {"check_same_thread": False}
    if database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def init_db(session: Session) -> None:
    # Create all database tables
    SQLModel.metadata.create_all(engine)

    # Create initial superuser if it doesn't exist
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

import uuid
from typing import Any

from sqlmodel import Session, col, func, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    ItemCreate,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBasePublic,
    KnowledgeBasesPublic,
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationPublic,
    ConversationsPublic,
    User,
    UserCreate,
    UserUpdate,
    Document,
    DocumentChunk
)
from datetime import UTC, datetime


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

def create_knowledge_base(
    *,
    session: Session,
    knowledge_base_in: KnowledgeBaseCreate,
    owner_id: uuid.UUID,
) -> KnowledgeBase:
    db_obj = KnowledgeBase.model_validate(
        knowledge_base_in,
        update={"owner_id": owner_id},
    )

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    return db_obj



def get_knowledge_bases(
    *,
    session: Session,
    owner_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> KnowledgeBasesPublic:
    # 统计当前用户拥有的知识库数量
    count_statement = (
        select(func.count())
        .select_from(KnowledgeBase)
        .where(KnowledgeBase.owner_id == owner_id)
    )
    count = session.exec(count_statement).one()

    # 查询当前用户的知识库，按创建时间倒序排列
    statement = (
        select(KnowledgeBase)
        .where(KnowledgeBase.owner_id == owner_id)
        .order_by(col(KnowledgeBase.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    knowledge_bases = session.exec(statement).all()

    # 返回公开模型
    knowledge_bases_public = [
        KnowledgeBasePublic.model_validate(item)
        for item in knowledge_bases
    ]

    return KnowledgeBasesPublic(
        data=knowledge_bases_public,
        count=count,
    )



def get_knowledge_base(
    *,
    session: Session,
    knowledge_base_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> KnowledgeBase | None:
    """Get a knowledge base owned by the specified user."""
    statement = select(KnowledgeBase).where(
        KnowledgeBase.id == knowledge_base_id,
        KnowledgeBase.owner_id == owner_id,
    )
    return session.exec(statement).first()


def update_knowledge_base(
    *,
    session: Session,
    db_knowledge_base: KnowledgeBase,
    knowledge_base_in: KnowledgeBaseUpdate,
) -> KnowledgeBase:
    """Update a knowledge base."""
    update_data = knowledge_base_in.model_dump(exclude_unset=True)

    db_knowledge_base.sqlmodel_update(update_data)

    session.add(db_knowledge_base)
    session.commit()
    session.refresh(db_knowledge_base)

    return db_knowledge_base


def delete_knowledge_base(
    *,
    session: Session,
    db_knowledge_base: KnowledgeBase,
) -> None:
    """Delete a knowledge base."""
    session.delete(db_knowledge_base)
    session.commit()

def create_document(
    *,
    session: Session,
    filename: str,
    content_type: str | None,
    size: int,
    storage_path: str,
    knowledge_base_id: uuid.UUID,
) -> Document:
    db_document = Document(
        filename=filename,
        content_type=content_type,
        size=size,
        storage_path=storage_path,
        knowledge_base_id=knowledge_base_id,
    )

    session.add(db_document)
    session.commit()
    session.refresh(db_document)

    return db_document


def get_document(
    *,
    session: Session,
    document_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
) -> Document | None:
    statement = select(Document).where(
        Document.id == document_id,
        Document.knowledge_base_id == knowledge_base_id,
    )
    return session.exec(statement).first()


def get_documents(
    *,
    session: Session,
    knowledge_base_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Document]:
    statement = (
        select(Document)
        .where(Document.knowledge_base_id == knowledge_base_id)
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def count_documents(
    *,
    session: Session,
    knowledge_base_id: uuid.UUID,
) -> int:
    statement = select(func.count()).select_from(Document).where(
        Document.knowledge_base_id == knowledge_base_id
    )
    return session.exec(statement).one()


def delete_document(
    *,
    session: Session,
    db_document: Document,
) -> None:
    session.delete(db_document)
    session.commit()



def create_document_chunks(
    *,
    session: Session,
    document_id: uuid.UUID,
    chunks: list[str],
) -> list[DocumentChunk]:
    db_chunks = [
        DocumentChunk(
            document_id=document_id,
            chunk_index=index,
            content=content,
            character_count=len(content),
        )
        for index, content in enumerate(chunks)
    ]

    session.add_all(db_chunks)
    session.flush()

    return db_chunks



def get_document_chunks(
    *,
    session: Session,
    document_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[DocumentChunk]:
    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(skip)
        .limit(limit)
    )

    return list(session.exec(statement).all())


def count_document_chunks(
    *,
    session: Session,
    document_id: uuid.UUID,
) -> int:
    statement = (
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )

    return session.exec(statement).one()



def delete_document_chunks(
    *,
    session: Session,
    document_id: uuid.UUID,
) -> None:
    statement = select(DocumentChunk).where(
        DocumentChunk.document_id == document_id
    )

    chunks = session.exec(statement).all()

    for chunk in chunks:
        session.delete(chunk)

    session.flush()

def create_conversation(
    *,
    session: Session,
    conversation_in: ConversationCreate,
    owner_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
) -> Conversation:
    """创建会话。"""

    db_obj = Conversation.model_validate(
        conversation_in,
        update={
            "owner_id": owner_id,
            "knowledge_base_id": knowledge_base_id,
        },
    )

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    return db_obj


def get_conversation(
    *,
    session: Session,
    conversation_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Conversation | None:
    """查询当前用户拥有的会话。"""

    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.owner_id == owner_id,
    )

    return session.exec(statement).first()


def get_conversations(
    *,
    session: Session,
    owner_id: uuid.UUID,
    knowledge_base_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> ConversationsPublic:
    """查询当前用户的会话列表。"""

    conditions = [Conversation.owner_id == owner_id]

    if knowledge_base_id is not None:
        conditions.append(
            Conversation.knowledge_base_id == knowledge_base_id
        )

    count_statement = (
        select(func.count())
        .select_from(Conversation)
        .where(*conditions)
    )

    count = session.exec(count_statement).one()

    statement = (
        select(Conversation)
        .where(*conditions)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )

    conversations = session.exec(statement).all()

    return ConversationsPublic(
        data=[
            ConversationPublic.model_validate(item)
            for item in conversations
        ],
        count=count,
    )


def update_conversation(
    *,
    session: Session,
    db_conversation: Conversation,
    conversation_in: ConversationUpdate,
) -> Conversation:
    """更新会话。"""

    update_data = conversation_in.model_dump(exclude_unset=True)

    db_conversation.sqlmodel_update(
        update_data,
        update={
            "updated_at": datetime.now(UTC),
        },
    )

    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)

    return db_conversation


def touch_conversation(
    *,
    session: Session,
    db_conversation: Conversation,
) -> Conversation:
    """更新会话最后活跃时间。"""

    db_conversation.updated_at = datetime.now(UTC)

    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)

    return db_conversation


def delete_conversation(
    *,
    session: Session,
    db_conversation: Conversation,
) -> None:
    """删除会话业务记录。"""

    session.delete(db_conversation)
    session.commit()

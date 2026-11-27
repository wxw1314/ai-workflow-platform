import uuid
from datetime import UTC, datetime

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, Text



def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)
    knowledge_bases: list["KnowledgeBase"] = Relationship(
      back_populates="owner",
      cascade_delete=True,
  )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")



# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

class KnowledgeBaseBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass


class KnowledgeBaseUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class KnowledgeBase(KnowledgeBaseBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime | None = Field(
        default_factory=get_datetime_utc
    )

    owner_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
    )

    owner: User | None = Relationship(
        back_populates="knowledge_bases"
    )

    documents: list["Document"] = Relationship(
        back_populates="knowledge_base",
        cascade_delete=True,
    )


class KnowledgeBasePublic(KnowledgeBaseBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class KnowledgeBasesPublic(SQLModel):
    data: list[KnowledgeBasePublic]
    count: int


class DocumentBase(SQLModel):
    filename: str = Field(max_length=500)
    content_type: str | None = Field(default=None, max_length=255)
    size: int | None = None

class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime | None = Field(
        default_factory=get_datetime_utc
    )

    # 文件在服务器上的相对存储路径
    storage_path: str = Field(max_length=1000)

    knowledge_base_id: uuid.UUID = Field(
        foreign_key="knowledgebase.id",
        nullable=False,
        ondelete="CASCADE",
    )

    knowledge_base: KnowledgeBase | None = Relationship(
        back_populates="documents"
    )
    chunks: list["DocumentChunk"] = Relationship(
        back_populates="document",
        cascade_delete=True,
    )

class DocumentPublic(DocumentBase):
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    created_at: datetime | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int


class DocumentChunk(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    document_id: uuid.UUID = Field(
        foreign_key="document.id",
        nullable=False,
        ondelete="CASCADE",
    )

    chunk_index: int = Field(nullable=False)

    content: str = Field(
        sa_column=Column(Text, nullable=False)
    )

    character_count: int = Field(nullable=False)

    created_at: datetime | None = Field(
        default_factory=get_datetime_utc
    )

    document: Document | None = Relationship(
        back_populates="chunks"
    )


class DocumentChunkPublic(SQLModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    character_count: int
    created_at: datetime | None = None


class DocumentChunksPublic(SQLModel):
    data: list[DocumentChunkPublic]
    count: int

class KnowledgeBaseSearchRequest(SQLModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class RetrievedChunkPublic(SQLModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    character_count: int
    score: float

class KnowledgeBaseAgentRequest(SQLModel):
    session_id: uuid.UUID
    query: str = Field(min_length=1, max_length=2000)

class KnowledgeBaseSearchResponse(SQLModel):
    data: list[RetrievedChunkPublic]
    count: int


class KnowledgeBaseAskResponse(SQLModel):
    answer: str
    sources: list[RetrievedChunkPublic]


class ConversationBase(SQLModel):
    title: str = Field(default="新建对话", min_length=1, max_length=255)


class Conversation(ConversationBase, table=True):
    """用户与知识库之间的一段 Agent 对话。"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    owner_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
        index=True,
    )

    knowledge_base_id: uuid.UUID = Field(
        foreign_key="knowledgebase.id",
        nullable=False,
        ondelete="CASCADE",
        index=True,
    )

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        nullable=False,
    )

    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        nullable=False,
    )


class ConversationCreate(SQLModel):
    title: str = Field(
        default="新建对话",
        min_length=1,
        max_length=255,
    )


class ConversationUpdate(SQLModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class ConversationPublic(ConversationBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ConversationCreateRequest(SQLModel):
    knowledge_base_id: uuid.UUID
    title: str = Field(default="新建对话", min_length=1, max_length=200)


class ConversationUpdateRequest(SQLModel):
    title: str = Field(min_length=1, max_length=200)


class ConversationPublic(SQLModel):
    id: uuid.UUID
    title: str
    owner_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ConversationsPublic(SQLModel):
    data: list[ConversationPublic]
    count: int


class ConversationMessagePublic(SQLModel):
    type: str
    content: str
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Conversation, KnowledgeBase


async def get_knowledge_base(
    *,
    session: AsyncSession,
    knowledge_base_id: UUID,
    owner_id: UUID,
) -> KnowledgeBase | None:
    statement = select(KnowledgeBase).where(
        KnowledgeBase.id == knowledge_base_id,
        KnowledgeBase.owner_id == owner_id,
    )

    result = await session.exec(statement)
    return result.first()


async def get_conversation(
    *,
    session: AsyncSession,
    conversation_id: UUID,
    owner_id: UUID,
) -> Conversation | None:
    """查询当前用户拥有的会话。"""
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.owner_id == owner_id,
    )

    result = await session.exec(statement)
    return result.first()


async def touch_conversation(
    *,
    session: AsyncSession,
    db_conversation: Conversation,
) -> Conversation:
    """更新会话最后活跃时间。"""
    db_conversation.updated_at = datetime.now(UTC)

    session.add(db_conversation)
    await session.commit()
    await session.refresh(db_conversation)

    return db_conversation

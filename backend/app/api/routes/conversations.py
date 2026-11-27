import uuid

from fastapi import APIRouter, HTTPException, Request, status
from langchain_core.messages import AIMessage, HumanMessage
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ConversationCreate,
    ConversationCreateRequest,
    ConversationPublic,
    ConversationsPublic,
    ConversationUpdate,
    ConversationUpdateRequest,
    KnowledgeBase,
)
from app.services.conversation_service import (
    build_conversation_thread_id,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post(
    "",
    response_model=ConversationPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: ConversationCreateRequest,
):
    # 1. 确认知识库存在，并且属于当前用户
    knowledge_base = session.exec(
        select(KnowledgeBase).where(
            KnowledgeBase.id == body.knowledge_base_id,
            KnowledgeBase.owner_id == current_user.id,
        )
    ).first()

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    # 2. 创建业务会话
    conversation = crud.create_conversation(
        session=session,
        conversation_in=ConversationCreate(title=body.title),
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base.id,
    )

    return conversation


@router.get("", response_model=ConversationsPublic)
def read_conversations(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
):
    conversations = crud.get_conversations(
        session=session,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        skip=skip,
        limit=limit,
    )

    return conversations


@router.get("/{conversation_id}", response_model=ConversationPublic)
def read_conversation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
):
    conversation = crud.get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


@router.patch("/{conversation_id}", response_model=ConversationPublic)
def update_conversation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
    body: ConversationUpdateRequest,
):
    conversation = crud.get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return crud.update_conversation(
        session=session,
        db_conversation=conversation,
        conversation_in=ConversationUpdate(title=body.title),
    )

@router.get("/{conversation_id}/messages")
async def read_conversation_messages(
    *,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
):
    # 1. 验证会话归属
    conversation = crud.get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # 2. 获取 Checkpointer
    checkpointer = getattr(
        request.app.state,
        "checkpointer",
        None,
    )

    if checkpointer is None:
        raise HTTPException(
            status_code=503,
            detail="Checkpointer is not available",
        )

    # 3. 构造与 Agent 相同的 thread_id
    thread_id = build_conversation_thread_id(
        owner_id=current_user.id,
        knowledge_base_id=conversation.knowledge_base_id,
        conversation_id=conversation.id,
    )

    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",
        }
    }

    # 4. 读取最新 checkpoint
    checkpoint_tuple = await checkpointer.aget_tuple(config)

    if checkpoint_tuple is None:
        return {
            "data": [],
            "count": 0,
        }

    # 5. 提取历史消息
    messages = (
        checkpoint_tuple.checkpoint
        .get("channel_values", {})
        .get("messages", [])
    )

    result = []

    for message in messages:
        # 只向前端展示用户消息和最终 AI 回复
        if isinstance(message, HumanMessage):
            result.append({
                "type": "human",
                "content": message.text,
            })

        elif isinstance(message, AIMessage):
            # 跳过 Agent 的工具调用中间消息
            if message.tool_calls:
                continue

            if message.content:
                result.append({
                    "type": "ai",
                    "content": message.text,
                })

    return {
        "data": result,
        "count": len(result),
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    *,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
    ):
    # 1. 验证会话归属
    conversation = crud.get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # 2. 获取 Checkpointer
    checkpointer = getattr(
        request.app.state,
        "checkpointer",
        None,
    )

    if checkpointer is None:
        raise HTTPException(
            status_code=503,
            detail="Checkpointer is not available",
        )

    # 3. 构造 thread_id
    thread_id = build_conversation_thread_id(
        owner_id=current_user.id,
        knowledge_base_id=conversation.knowledge_base_id,
        conversation_id=conversation.id,
    )

    # 4. 删除 LangGraph checkpoint
    try:
        checkpointer.delete_thread(thread_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete conversation checkpoint",
        ) from exc

    # 5. 删除 Conversation 业务记录
    crud.delete_conversation(
        session=session,
        db_conversation=conversation,
    )

    return {
        "message": "Conversation deleted successfully"
    }

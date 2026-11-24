from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    KnowledgeBaseAgentRequest,
    KnowledgeBaseAskResponse,
    RetrievedChunkPublic,
)
from app.services.agent_service import agent_service
from app.services.conversation_service import (
    build_conversation_thread_id,
)

router = APIRouter(tags=["knowledge-base-agent"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/agent",
    response_model=KnowledgeBaseAskResponse,
)
def run_knowledge_base_agent(
    *,
    request: Request,
    session: SessionDep,
    knowledge_base_id: UUID,
    body: KnowledgeBaseAgentRequest,
    current_user: CurrentUser,
):
    # 1. 验证知识库归属
    knowledge_base = crud.get_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        owner_id=current_user.id,
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    # 2. 验证会话是否存在，以及是否属于当前用户
    conversation = crud.get_conversation(
        session=session,
        conversation_id=body.session_id,
        owner_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    # 3. 验证会话是否属于当前知识库
    if conversation.knowledge_base_id != knowledge_base_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to this knowledge base",
        )

    # 4. 获取 LangGraph Checkpointer
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

    # 5. 统一生成 thread_id
    thread_id = build_conversation_thread_id(
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        conversation_id=conversation.id,
    )

    # 6. 执行 Agent
    result = agent_service.ask(
        session=session,
        knowledge_base_id=knowledge_base_id,
        query=body.query,
        thread_id=thread_id,
        checkpointer=checkpointer,
    )

    # 7. 更新会话最后活跃时间
    crud.touch_conversation(
        session=session,
        db_conversation=conversation,
    )

    sources = [
        RetrievedChunkPublic.model_validate(item)
        for item in result["sources"]
    ]

    return KnowledgeBaseAskResponse(
        answer=result["answer"],
        sources=sources,
    )

import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app import crud_async
from app.api.deps import AsyncSessionDep, CurrentUserAsync
from app.models import (
    KnowledgeBaseAgentRequest,
    KnowledgeBaseAskResponse,
    RetrievedChunkPublic,
)
from app.services.agent_service import agent_service
from app.services.conversation_service import build_conversation_thread_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge-base-agent"])


async def _get_agent_context(
    *,
    session: AsyncSessionDep,
    knowledge_base_id: UUID,
    body: KnowledgeBaseAgentRequest,
    current_user: CurrentUserAsync,
    request: Request,
):
    """验证知识库、会话归属，并获取 Checkpointer。"""

    knowledge_base = await crud_async.get_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        owner_id=current_user.id,
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    conversation = await crud_async.get_conversation(
        session=session,
        conversation_id=body.session_id,
        owner_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    if conversation.knowledge_base_id != knowledge_base_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to this knowledge base",
        )

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

    thread_id = build_conversation_thread_id(
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        conversation_id=conversation.id,
    )

    return conversation, checkpointer, thread_id


@router.post(
    "/knowledge-bases/{knowledge_base_id}/agent",
    response_model=KnowledgeBaseAskResponse,
)
async def run_knowledge_base_agent(
    *,
    request: Request,
    session: AsyncSessionDep,
    knowledge_base_id: UUID,
    body: KnowledgeBaseAgentRequest,
    current_user: CurrentUserAsync,
):
    conversation, checkpointer, thread_id = await _get_agent_context(
        session=session,
        knowledge_base_id=knowledge_base_id,
        body=body,
        current_user=current_user,
        request=request,
    )

    result = await agent_service.ask(
        session=session,
        knowledge_base_id=knowledge_base_id,
        query=body.query,
        thread_id=thread_id,
        checkpointer=checkpointer,
    )

    await crud_async.touch_conversation(
        session=session,
        db_conversation=conversation,
    )

    sources = [RetrievedChunkPublic.model_validate(item) for item in result["sources"]]

    return KnowledgeBaseAskResponse(
        answer=result["answer"],
        sources=sources,
    )


@router.post(
    "/knowledge-bases/{knowledge_base_id}/agent/stream",
)
async def stream_knowledge_base_agent(
    *,
    request: Request,
    session: AsyncSessionDep,
    knowledge_base_id: UUID,
    body: KnowledgeBaseAgentRequest,
    current_user: CurrentUserAsync,
):
    conversation, checkpointer, thread_id = await _get_agent_context(
        session=session,
        knowledge_base_id=knowledge_base_id,
        body=body,
        current_user=current_user,
        request=request,
    )

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in agent_service.stream(
                session=session,
                knowledge_base_id=knowledge_base_id,
                query=body.query,
                thread_id=thread_id,
                checkpointer=checkpointer,
            ):
                if event["event"] == "done":
                    await crud_async.touch_conversation(
                        session=session,
                        db_conversation=conversation,
                    )

                yield (
                    f"event: {event['event']}\n"
                    f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                )

        except Exception:
            logger.exception("Agent streaming execution failed")

            await session.rollback()

            yield (
                "event: error\n"
                f"data: {json.dumps({'message': 'Agent execution failed'}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

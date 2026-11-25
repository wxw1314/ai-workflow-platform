from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import crud_async
from app.api.deps import AsyncSessionDep, CurrentUserAsync
from app.models import (
    KnowledgeBaseAskResponse,
    KnowledgeBaseSearchRequest,
    RetrievedChunkPublic,
)
from app.services.rag_service import rag_service


router = APIRouter(tags=["knowledge-base"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/ask",
    response_model=KnowledgeBaseAskResponse,
)
async def ask_knowledge_base(
    *,
    session: AsyncSessionDep,
    knowledge_base_id: UUID,
    request: KnowledgeBaseSearchRequest,
    current_user: CurrentUserAsync,
) -> KnowledgeBaseAskResponse:
    # 1. 检查知识库是否存在，以及当前用户是否拥有该知识库
    knowledge_base = await crud_async.get_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        owner_id=current_user.id,
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    # 2. 执行异步 RAG 问答
    result = await rag_service.ask(
        session=session,
        query=request.query,
        knowledge_base_id=knowledge_base_id,
        limit=request.limit,
    )

    # 3. 转换来源数据
    sources = [
        RetrievedChunkPublic.model_validate(source)
        for source in result["sources"]
    ]

    # 4. 返回答案和引用来源
    return KnowledgeBaseAskResponse(
        answer=result["answer"],
        sources=sources,
    )
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app import crud_async
from app.api.deps import AsyncSessionDep, CurrentUserAsync
from app.models import (
    KnowledgeBaseSearchRequest,
    KnowledgeBaseSearchResponse,
    RetrievedChunkPublic,
)
from app.services.retrieval_service import retrieve_chunks


router = APIRouter(tags=["knowledge-base"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/search",
    response_model=KnowledgeBaseSearchResponse,
)
async def search_knowledge_base(
    *,
    session: AsyncSessionDep,
    knowledge_base_id: UUID,
    request: KnowledgeBaseSearchRequest,
    current_user: CurrentUserAsync,
) -> KnowledgeBaseSearchResponse:
    # 1. 检查知识库是否存在，以及当前用户是否有权访问
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

    # 2. 执行异步语义检索
    results = await retrieve_chunks(
        session=session,
        query=request.query,
        knowledge_base_id=knowledge_base_id,
        limit=request.limit,
    )

    # 3. 转换 API 响应
    data = [
        RetrievedChunkPublic(**item)
        for item in results
    ]

    return KnowledgeBaseSearchResponse(
        data=data,
        count=len(data),
    )
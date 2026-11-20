from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import crud
from app.api import deps
from app.models import (
    KnowledgeBaseSearchRequest,
    KnowledgeBaseSearchResponse,
    RetrievedChunkPublic,
)
from app.services.retrieval_service import retrieve_chunks

from app.api.deps import CurrentUser,SessionDep

router = APIRouter(tags=['knowledge-base'])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/search",
    response_model=KnowledgeBaseSearchResponse,
)
def search_knowledge_base(
    *,
    session: SessionDep,
    knowledge_base_id: UUID,
    request: KnowledgeBaseSearchRequest,
    current_user: CurrentUser,
):
    # 1. 检查知识库是否存在，以及当前用户是否有权访问
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

    # 2. 执行语义检索
    results = retrieve_chunks(
        session=session,
        query=request.query,
        knowledge_base_id=knowledge_base_id,
        limit=request.limit,
    )

    # 3. 转换成 API 响应模型
    data = [
        RetrievedChunkPublic(**item)
        for item in results
    ]

    return KnowledgeBaseSearchResponse(
        data=data,
        count=len(data),
    )
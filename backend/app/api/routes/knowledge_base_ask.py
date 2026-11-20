
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import crud
from app.api import deps
from app.api.deps import CurrentUser,SessionDep
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
def ask_knowledge_base(
    *,
    session:  SessionDep,
    knowledge_base_id: UUID,
    request: KnowledgeBaseSearchRequest,
    current_user: CurrentUser,
) -> KnowledgeBaseAskResponse:
    # 1. 检查知识库是否存在，以及当前用户是否拥有该知识库
    knowledge_base = crud.get_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        owner_id=current_user.id,
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    # 2. 执行 RAG 问答
    result = rag_service.ask(
        session=session,
        query=request.query,
        knowledge_base_id=str(knowledge_base_id),
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

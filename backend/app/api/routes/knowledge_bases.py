
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    KnowledgeBaseCreate,
    KnowledgeBasePublic,
    KnowledgeBaseUpdate,
    KnowledgeBasesPublic,
    Message,
)


router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge-bases"],
)


@router.post("/", response_model=KnowledgeBasePublic)
def create_knowledge_base(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_in: KnowledgeBaseCreate,
) -> Any:
    """
    Create a new knowledge base for the current user.
    """
    return crud.create_knowledge_base(
        session=session,
        knowledge_base_in=knowledge_base_in,
        owner_id=current_user.id,
    )


@router.get("/", response_model=KnowledgeBasesPublic)
def read_knowledge_bases(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve knowledge bases belonging to the current user.
    """
    return crud.get_knowledge_bases(
        session=session,
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=KnowledgeBasePublic)
def read_knowledge_base(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    """
    Get a specific knowledge base owned by the current user.
    """
    knowledge_base = crud.get_knowledge_base(
        session=session,
        knowledge_base_id=id,
        owner_id=current_user.id,
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    return knowledge_base


@router.patch("/{id}", response_model=KnowledgeBasePublic)
def update_knowledge_base(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    knowledge_base_in: KnowledgeBaseUpdate,
) -> Any:
    """
    Update a knowledge base owned by the current user.
    """
    knowledge_base = crud.get_knowledge_base(
        session=session,
        knowledge_base_id=id,
        owner_id=current_user.id,
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    return crud.update_knowledge_base(
        session=session,
        db_knowledge_base=knowledge_base,
        knowledge_base_in=knowledge_base_in,
    )


@router.delete("/{id}", response_model=Message)
def delete_knowledge_base(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Message:
    """
    Delete a knowledge base owned by the current user.
    """
    knowledge_base = crud.get_knowledge_base(
        session=session,
        knowledge_base_id=id,
        owner_id=current_user.id,
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    crud.delete_knowledge_base(
        session=session,
        db_knowledge_base=knowledge_base,
    )

    return Message(message="Knowledge base deleted successfully")

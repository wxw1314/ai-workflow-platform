import logging
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Document, 
    DocumentPublic, 
    DocumentsPublic, 
    DocumentChunksPublic
)
from app.services.document_service import (
    delete_document_file,
    save_document_file,
    validate_filename,
)

from app.services.document_processing import process_document

router = APIRouter(tags=["documents"])
logger = logging.getLogger(__name__)


def get_owned_knowledge_base(
    *,
    session: SessionDep,
    knowledge_base_id: UUID,
    user_id: UUID,
):
    knowledge_base = crud.get_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        owner_id=user_id,
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    return knowledge_base


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: UUID,
    file: UploadFile = File(...),
):
    # 1. 验证知识库属于当前用户
    get_owned_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    # 2. 验证文件扩展名
    try:
        validate_filename(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # 3. 生成文档 ID，并保存真实文件
    import uuid

    document_id = uuid.uuid4()

    try:
        storage_path, file_size = await save_document_file(
            upload_file=file,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    finally:
        await file.close()

    # 4. 保存文件元数据
    try:
        document = Document(
            id=document_id,
            filename=file.filename or "unnamed",
            content_type=file.content_type,
            size=file_size,
            storage_path=storage_path,
            knowledge_base_id=knowledge_base_id,
        )

        session.add(document)
        session.commit()
        session.refresh(document)

        return document

    except Exception:
        session.rollback()

        try:
            delete_document_file(storage_path)
        except OSError:
            logger.exception("Failed to clean up uploaded file")

        raise

@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentsPublic,
)
def read_documents(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: UUID,
    skip: int = 0,
    limit: int = 100,
):
    get_owned_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    if skip < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters",
        )

    documents = crud.get_documents(
        session=session,
        knowledge_base_id=knowledge_base_id,
        skip=skip,
        limit=limit,
    )

    count = crud.count_documents(
        session=session,
        knowledge_base_id=knowledge_base_id,
    )

    return DocumentsPublic(data=documents, count=count)


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    response_model=DocumentPublic,
)
def read_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: UUID,
    document_id: UUID,
):
    get_owned_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    document = crud.get_document(
        session=session,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: UUID,
    document_id: UUID,
):
    get_owned_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    document = crud.get_document(
        session=session,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # 先删除数据库记录，再删除磁盘文件。
    # 如果磁盘删除失败，记录日志，后续可以通过清理任务处理孤儿文件。
    storage_path = document.storage_path
    crud.delete_document(session=session, db_document=document)

    try:
        delete_document_file(storage_path)
    except OSError:
        logger.exception(
            "Document record deleted, but file cleanup failed: %s",
            storage_path,
        )

@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/process",
    response_model=DocumentChunksPublic,
)
def process_document_endpoint(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: UUID,
    document_id: UUID,
):
    get_owned_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    document = crud.get_document(
        session=session,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        chunks = process_document(
            session=session,
            document=document,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return DocumentChunksPublic(
        data=chunks,
        count=len(chunks),
    )

@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}/chunks",
    response_model=DocumentChunksPublic,
)
def read_document_chunks(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    knowledge_base_id: UUID,
    document_id: UUID,
    skip: int = 0,
    limit: int = 100,
):
    get_owned_knowledge_base(
        session=session,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    document = crud.get_document(
        session=session,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if skip < 0 or limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters",
        )

    chunks = crud.get_document_chunks(
        session=session,
        document_id=document_id,
        skip=skip,
        limit=limit,
    )

    count = crud.count_document_chunks(
        session=session,
        document_id=document_id,
    )

    return DocumentChunksPublic(
        data=chunks,
        count=count,
    )

import logging
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select

from app import crud
from app.models import Document, DocumentChunk
from app.services.document_parser import extract_text
from app.services.embedding_service import qwen_embeddings
from app.services.text_splitter import split_text
from app.services.vector_store_service import milvus_vector_store

logger = logging.getLogger(__name__)


def get_safe_document_path(storage_path: str) -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    uploads_root = (backend_root / "uploads").resolve()
    file_path = (backend_root / storage_path).resolve()

    if not file_path.is_relative_to(uploads_root):
        raise ValueError("Invalid document storage path")

    return file_path


def process_document(
    *,
    session: Session,
    document: Document,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[DocumentChunk]:
    file_path = get_safe_document_path(document.storage_path)

    # 1. 提取文本并切片
    text = extract_text(file_path, document.filename)
    chunks = split_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    if not chunks:
        raise ValueError("Document produced no text chunks")

    new_chunk_ids: list[str] = []
    vectors_inserted = False

    try:
        # 2. 查询旧 Chunk，记录它们的 ID
        statement = select(DocumentChunk).where(
            DocumentChunk.document_id == document.id
        )
        old_chunks = session.exec(statement).all()
        old_chunk_ids = [str(chunk.id) for chunk in old_chunks]

        # 3. 删除旧 Chunk，创建新 Chunk
        crud.delete_document_chunks(
            session=session,
            document_id=document.id,
        )

        new_chunks = crud.create_document_chunks(
            session=session,
            document_id=document.id,
            chunks=chunks,
        )

        # flush 后新 Chunk 已经有 ID，但事务尚未提交
        new_chunk_ids = [str(chunk.id) for chunk in new_chunks]

        # 4. 调用 Embedding API
        texts = [chunk.content for chunk in new_chunks]
        embeddings = qwen_embeddings.embed_documents(texts)

        # 5. 写入 Milvus
        milvus_vector_store.insert_chunks(
            chunks=new_chunks,
            embeddings=embeddings,
            knowledge_base_id=str(document.knowledge_base_id),
        )
        vectors_inserted = True

        # 6. 提交 PostgreSQL 事务
        session.commit()

    except Exception:
        session.rollback()

        # PostgreSQL 提交失败时，清理本次新写入的向量
        if vectors_inserted:
            try:
                milvus_vector_store.delete_vectors_by_chunk_ids(
                    new_chunk_ids
                )
            except Exception:
                logger.exception(
                    "Failed to clean up new vectors after processing failure"
                )

        raise

    # 7. PostgreSQL 已提交，再清理旧向量
    if old_chunk_ids:
        try:
            milvus_vector_store.delete_vectors_by_chunk_ids(
                old_chunk_ids
            )
        except Exception:
            # 清理失败不影响已经成功的文档处理结果
            logger.exception(
                "Failed to clean up old vectors for document %s",
                document.id,
            )

    return new_chunks

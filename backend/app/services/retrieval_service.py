
from uuid import UUID

from sqlmodel import Session, select

from app.models import Document, DocumentChunk
from app.services.embedding_service import qwen_embeddings
from app.services.vector_store_service import milvus_vector_store


def retrieve_chunks(
    *,
    session: Session,
    query: str,
    knowledge_base_id: UUID,
    limit: int = 5,
) -> list[dict]:
    if not query.strip():
        raise ValueError("Query cannot be empty")

    if limit < 1:
        raise ValueError("Limit must be greater than 0")

    # 1. 将用户问题转换成向量
    query_embedding = qwen_embeddings.embed_query(query)

    # 2. 在 Milvus 中搜索相似向量
    search_results = milvus_vector_store.search(
        query_embedding=query_embedding,
        knowledge_base_id=str(knowledge_base_id),
        limit=limit,
    )

    if not search_results:
        return []

    # 3. 提取 Chunk ID
    chunk_ids = [
        UUID(item["chunk_id"])
        for item in search_results
    ]

    # PostgreSQL 查询原文，并验证知识库归属
    statement = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.content,
            DocumentChunk.character_count,
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            DocumentChunk.id.in_(chunk_ids),
            Document.knowledge_base_id == knowledge_base_id,
        )
    )

    db_chunks = session.exec(statement).all()

    # 建立 ID 到查询结果的映射
    chunk_map = {
        str(chunk.id): chunk  
        for chunk in db_chunks
    }

    # 按照 Milvus 的相似度排序返回
    retrieved_chunks = []

    for result in search_results:
        chunk = chunk_map.get(result["chunk_id"])

        if chunk is None:
            continue

        retrieved_chunks.append({
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "content": chunk.content,
            "character_count": chunk.character_count,
            "score": result["score"],
        })


    return retrieved_chunks
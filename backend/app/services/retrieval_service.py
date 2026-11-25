import asyncio
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Document, DocumentChunk
from app.services.embedding_service import qwen_embeddings
from app.services.vector_store_service import milvus_vector_store


async def retrieve_chunks(
    *,
    session: AsyncSession,
    query: str,
    knowledge_base_id: UUID,
    limit: int = 5,
) -> list[dict]:
    if not query.strip():
        raise ValueError("Query cannot be empty")

    if limit < 1:
        raise ValueError("Limit must be greater than 0")

    # 1. 异步调用 Embedding API
    query_embedding = await qwen_embeddings.aembed_query(query)

    # 2. 将同步 Milvus 搜索放到线程池
    search_results = await asyncio.to_thread(
        milvus_vector_store.search,
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

    # 4. 异步查询 PostgreSQL，并验证知识库归属
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

    result = await session.exec(statement)
    db_chunks = result.all()

    chunk_map = {
        str(chunk.id): chunk
        for chunk in db_chunks
    }

    # 5. 按 Milvus 相似度顺序返回
    retrieved_chunks = []

    for item in search_results:
        chunk = chunk_map.get(item["chunk_id"])

        if chunk is None:
            continue

        retrieved_chunks.append({
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "content": chunk.content,
            "character_count": chunk.character_count,
            "score": item["score"],
        })

    return retrieved_chunks
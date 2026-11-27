import asyncio
import logging
from collections.abc import Callable
from uuid import UUID

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Document, DocumentChunk
from app.services.embedding_service import qwen_embeddings
from app.services.retry_service import (
    is_retryable_database_error,
    retry_async,
    retry_sync,
)
from app.services.vector_store_service import milvus_vector_store

logger = logging.getLogger(__name__)
RetryCallback = Callable[[int, Exception, float, str], None]


class RetrievalServiceError(Exception):
    def __init__(
        self, code: str, message: str, *, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _notify_retry(
    callback: RetryCallback | None, service: str
) -> Callable[[int, Exception, float], None] | None:
    if callback is None:
        return None

    def notify(attempt: int, exc: Exception, delay: float) -> None:
        callback(attempt, exc, delay, service)

    return notify


def _classify_embedding_error(exc: Exception) -> RetrievalServiceError:
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return RetrievalServiceError(
            "EMBEDDING_AUTH_ERROR", "Embedding 服务认证或权限配置异常。"
        )
    if isinstance(exc, RateLimitError):
        return RetrievalServiceError(
            "EMBEDDING_RATE_LIMITED",
            "Embedding 服务当前请求过多，请稍后再试。",
            retryable=True,
        )
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return RetrievalServiceError(
            "EMBEDDING_CONNECTION_ERROR",
            "Embedding 服务暂时无法连接。",
            retryable=True,
        )
    if isinstance(exc, BadRequestError):
        return RetrievalServiceError(
            "EMBEDDING_BAD_REQUEST", "Embedding 请求参数不正确。"
        )
    if isinstance(exc, APIStatusError):
        if exc.status_code >= 500:
            return RetrievalServiceError(
                "EMBEDDING_SERVER_ERROR",
                "Embedding 服务暂时不可用。",
                retryable=True,
            )
        return RetrievalServiceError(
            "EMBEDDING_API_ERROR", "Embedding 服务请求失败。"
        )
    return RetrievalServiceError("EMBEDDING_ERROR", "Embedding 处理失败。")


async def retrieve_chunks(
    *,
    session: AsyncSession,
    query: str,
    knowledge_base_id: UUID,
    limit: int = 5,
    on_retry: RetryCallback | None = None,
) -> list[dict]:
    if not query.strip():
        raise ValueError("Query cannot be empty")
    if limit < 1:
        raise ValueError("Limit must be greater than 0")

    # 1. Embedding：SDK max_retries 应设为 0，由应用层统一控制。
    try:
        query_embedding = await retry_async(
            lambda: qwen_embeddings.aembed_query(query),
            max_attempts=3,
            base_delay=1.0,
            max_delay=8.0,
            on_retry=_notify_retry(on_retry, "embedding"),
        )
    except Exception as exc:
        logger.exception("Embedding request failed")
        raise _classify_embedding_error(exc) from exc

    # 2. Milvus：同步 SDK 放入工作线程，避免阻塞事件循环。
    try:
        search_results = await asyncio.to_thread(
            retry_async_milvus_search,
            query_embedding,
            str(knowledge_base_id),
            limit,
            on_retry,
        )
    except Exception as exc:
        logger.exception("Milvus search failed")
        raise RetrievalServiceError(
            "VECTOR_SEARCH_UNAVAILABLE",
            "Milvus 向量检索服务暂时不可用，或检索配置存在问题。",
            retryable=True,
        ) from exc

    if not search_results:
        return []

    chunk_ids = [UUID(item["chunk_id"]) for item in search_results]
    statement = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.content,
            DocumentChunk.character_count,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.id.in_(chunk_ids),
            Document.knowledge_base_id == knowledge_base_id,
        )
    )

    # 3. PostgreSQL：仅对明确的连接中断、08xxx、序列化失败和死锁重试。
    async def query_postgres():
        try:
            result = await session.exec(statement)
            return result.all()
        except Exception:
            # 失败事务必须 rollback，才能尝试下一次。
            await session.rollback()
            raise

    try:
        db_chunks = await retry_async(
            query_postgres,
            max_attempts=3,
            base_delay=0.5,
            max_delay=4.0,
            on_retry=_notify_retry(on_retry, "postgresql"),
            retry_if=is_retryable_database_error,
        )
    except Exception as exc:
        await session.rollback()
        if is_retryable_database_error(exc):
            logger.exception("PostgreSQL retrieval unavailable after retries")
            raise RetrievalServiceError(
                "DATABASE_UNAVAILABLE",
                "PostgreSQL 数据库连接暂时不可用，检索未能完成。",
                retryable=True,
            ) from exc
        logger.exception("PostgreSQL retrieval query failed")
        raise

    chunk_map = {str(chunk.id): chunk for chunk in db_chunks}
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


def retry_async_milvus_search(
    query_embedding: list[float],
    knowledge_base_id: str,
    limit: int,
    on_retry: RetryCallback | None = None,
) -> list[dict]:
    return retry_sync(
        lambda: milvus_vector_store.search(
            query_embedding=query_embedding,
            knowledge_base_id=knowledge_base_id,
            limit=limit,
        ),
        max_attempts=3,
        base_delay=0.5,
        max_delay=4.0,
        on_retry=_notify_retry(on_retry, "milvus"),
    )

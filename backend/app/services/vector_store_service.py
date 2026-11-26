
from typing import Any
import json
from pymilvus import DataType, MilvusClient
from app.services.retry_service import retry_sync
from app.core.config import settings
from app.models import DocumentChunk


class MilvusVectorStore:
    COLLECTION_NAME = "knowledge_chunks"
    DIMENSION = 1024

    def __init__(self) -> None:
        self.client = MilvusClient(
            uri=settings.MILVUS_URI,
            token=settings.MILVUS_TOKEN or None,
        )

    def ensure_collection(self) -> None:
        if not self.client.has_collection(
            collection_name=self.COLLECTION_NAME
        ):
            schema = self.client.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )

            schema.add_field(
                field_name="chunk_id",
                datatype=DataType.VARCHAR,
                is_primary=True,
                max_length=36,
            )
            schema.add_field(
                field_name="document_id",
                datatype=DataType.VARCHAR,
                max_length=36,
            )
            schema.add_field(
                field_name="knowledge_base_id",
                datatype=DataType.VARCHAR,
                max_length=36,
            )
            schema.add_field(
                field_name="embedding",
                datatype=DataType.FLOAT_VECTOR,
                dim=self.DIMENSION,
            )

            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="AUTOINDEX",
                metric_type="COSINE",
            )

            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                schema=schema,
                index_params=index_params,
            )

        # 无论 Collection 是新建还是已经存在，都确保它已加载
        self.client.load_collection(
            collection_name=self.COLLECTION_NAME
        )

    
    def insert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        knowledge_base_id: str,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks count must match embeddings count")

        if not chunks:
            return 0

        self.ensure_collection()

        data = []

        for chunk, embedding in zip(chunks, embeddings):
            if len(embedding) != self.DIMENSION:
                raise ValueError(
                    f"Expected {self.DIMENSION} dimensions, "
                    f"got {len(embedding)}"
                )

            data.append({
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "knowledge_base_id": knowledge_base_id,
                "embedding": embedding,
            })

        result = self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            data=data,
        )

        return result["upsert_count"]


    def delete_document_vectors(
        self,
        document_id: str,
    ) -> int:
        """删除某个文档对应的全部向量。"""

        self.ensure_collection()

        result = self.client.delete(
            collection_name=self.COLLECTION_NAME,
            filter=f'document_id == "{document_id}"',
        )

        return result.get("delete_count", 0)

    
    def search(
        self,
        query_embedding: list[float],
        knowledge_base_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        self.ensure_collection()

        if len(query_embedding) != self.DIMENSION:
            raise ValueError(
                f"Expected {self.DIMENSION} dimensions, "
                f"got {len(query_embedding)}"
            )

        if limit < 1:
            raise ValueError("limit must be greater than 0")

        results = retry_sync(
            lambda: self.client.search(
                collection_name=self.COLLECTION_NAME,
                data=[query_embedding],
                filter=f'knowledge_base_id == "{knowledge_base_id}"',
                limit=limit,
                output_fields=[
                    "document_id",
                    "knowledge_base_id",
                ],
                search_params={
                    "metric_type": "COSINE",
                    "params": {},
                },
            ),
            max_attempts=3,
        )

        hits = results[0] if results else []

        return [
            {
                "chunk_id": hit["chunk_id"],
                "document_id": hit["entity"]["document_id"],
                "knowledge_base_id": hit["entity"]["knowledge_base_id"],
                "score": hit["distance"],
            }
            for hit in hits
        ]



    def delete_vectors_by_chunk_ids(
        self,
        chunk_ids: list[str],
    ) -> int:
        if not chunk_ids:
            return 0

        self.ensure_collection()

        filter_expression = f"chunk_id in {json.dumps(chunk_ids)}"

        result = self.client.delete(
            collection_name=self.COLLECTION_NAME,
            filter=filter_expression,
        )

        return result.get("delete_count", 0)

milvus_vector_store = MilvusVectorStore()

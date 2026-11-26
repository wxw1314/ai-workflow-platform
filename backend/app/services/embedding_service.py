from openai import AsyncOpenAI, OpenAI
from langchain_core.embeddings import Embeddings

from app.core.config import settings


class QwenEmbeddings(Embeddings):
    """
    使用阿里云百炼 Qwen Embedding API 的 LangChain 封装。
    同时支持同步和异步调用。
    """

    MODEL_NAME = "qwen3.7-text-embedding-flash"
    DIMENSIONS = 1024
    BATCH_SIZE = 20

    def __init__(self) -> None:
        base_url = (
            f"https://{settings.DASHSCOPE_WORKSPACE_ID}"
            ".cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        )

        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=base_url,
            max_retries=2,
            timeout=30.0,
        )

        self.async_client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=base_url,
            timeout=30.0,
            max_retries=0,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[start : start + self.BATCH_SIZE]

            response = self.client.embeddings.create(
                model=self.MODEL_NAME,
                input=batch,
                dimensions=self.DIMENSIONS,
            )

            ordered_data = sorted(
                response.data,
                key=lambda item: item.index,
            )

            all_embeddings.extend(
                item.embedding for item in ordered_data
            )

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Query text cannot be empty")

        response = self.client.embeddings.create(
            model=self.MODEL_NAME,
            input=[text],
            dimensions=self.DIMENSIONS,
        )

        return response.data[0].embedding

    async def aembed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Query text cannot be empty")

        response = await self.async_client.embeddings.create(
            model=self.MODEL_NAME,
            input=[text],
            dimensions=self.DIMENSIONS,
        )

        return response.data[0].embedding


qwen_embeddings = QwenEmbeddings()
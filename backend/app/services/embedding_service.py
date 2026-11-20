
from openai import OpenAI
from langchain_core.embeddings import Embeddings

from app.core.config import settings


class QwenEmbeddings(Embeddings):
    """
    使用阿里云百炼 Qwen Embedding API 的 LangChain 封装。
    """

    MODEL_NAME = "qwen3.7-text-embedding-flash"
    DIMENSIONS = 1024
    BATCH_SIZE = 20

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=(
                f"https://{settings.DASHSCOPE_WORKSPACE_ID}"
                ".cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
            ),
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        将多条文档文本转换成向量。
        自动分批，每次最多发送 20 条。
        """
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

            # 按照原始输入顺序整理向量
            ordered_data = sorted(
                response.data,
                key=lambda item: item.index,
            )

            batch_embeddings = [
                item.embedding for item in ordered_data
            ]

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """
        将用户查询文本转换成向量。
        """
        if not text.strip():
            raise ValueError("Query text cannot be empty")

        response = self.client.embeddings.create(
            model=self.MODEL_NAME,
            input=[text],
            dimensions=self.DIMENSIONS,
        )

        return response.data[0].embedding


# 创建可复用的 Embedding 服务实例
qwen_embeddings = QwenEmbeddings()



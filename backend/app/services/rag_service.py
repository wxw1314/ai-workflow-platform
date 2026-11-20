
from typing import Any

from langchain.chat_models import init_chat_model
from sqlmodel import Session

from app.core.config import settings
from app.services.retrieval_service import retrieve_chunks


class RAGService:
    MODEL_NAME = "qwen-turbo"

    def __init__(self) -> None:
        self.chat_model = init_chat_model(
            model=settings.BAIYOU_MODEL,
            model_provider="openai",
            base_url=settings.BAIYOU_BASE_URL,
            api_key=settings.BAIYOU_API_KEY,
            temperature=0.2,
            max_retries=2,
            timeout=60,
        )

    def build_context(
        self,
        chunks: list[dict[str, Any]],
    ) -> str:
        """将检索到的 Chunk 整理成模型可读的上下文。"""
        context_parts = []

        for index, chunk in enumerate(chunks, start=1):
            context_parts.append(
                f"""
              [参考资料 {index}]
              Chunk ID: {chunk["chunk_id"]}
              Document ID: {chunk["document_id"]}
              内容：
              {chunk["content"]}
              """
            )

        return "\n".join(context_parts)

    def generate_answer(self, query: str, context: str) -> str:
        system_prompt = """
    你是一个专业的知识库问答助手。

    请严格根据提供的知识库上下文回答用户问题。

    要求：
    1. 优先依据知识库上下文回答。
    2. 不要编造上下文中没有的信息。
    3. 如果上下文无法回答问题，请明确说明。
    4. 使用清晰、自然的中文回答。
    """

        user_prompt = f"""
          知识库上下文：

          {context}

          用户问题：

          {query}
          """

        response = self.chat_model.invoke([
            ("system", system_prompt),
            ("user", user_prompt),
        ])

        return str(response.content)

    def ask(
        self,
        session: Session,
        query: str,
        knowledge_base_id: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """执行完整的 RAG 问答流程。"""

        # 1. 检索相关知识片段
        chunks = retrieve_chunks(
            session=session,
            query=query,
            knowledge_base_id=knowledge_base_id,
            limit=limit,
        )

        # 2. 没有检索到资料，不调用大模型
        if not chunks:
            return {
                "answer": "知识库中没有找到与问题相关的资料，暂时无法回答。",
                "sources": [],
            }

        # 3. 构建上下文
        context = self.build_context(chunks)

        # 4. 调用大模型生成答案
        answer = self.generate_answer(
            query=query,
            context=context,
        )

        # 5. 返回答案和引用来源
        return {
            "answer": answer,
            "sources": chunks,
        }


rag_service = RAGService()

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessageChunk, SystemMessage
from langchain_core.tools import tool
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.services.retrieval_service import retrieve_chunks


class AgentService:
    """基于 LangGraph 的知识库 ReAct Agent。"""

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

    def _build_tools(
        self,
        *,
        session: AsyncSession,
        knowledge_base_id: UUID,
        retrieved_sources: list[dict],
    ):
        """创建绑定当前请求上下文的异步工具。"""

        @tool
        async def search_knowledge_base(query: str) -> str:
            """搜索当前知识库，获取与用户问题相关的资料。"""

            chunks = await retrieve_chunks(
                session=session,
                query=query,
                knowledge_base_id=knowledge_base_id,
                limit=5,
            )

            existing_ids = {item["chunk_id"] for item in retrieved_sources}

            for chunk in chunks:
                if chunk["chunk_id"] not in existing_ids:
                    retrieved_sources.append(chunk)
                    existing_ids.add(chunk["chunk_id"])

            if not chunks:
                return "知识库中没有检索到相关资料。请如实告知用户。"

            context = []

            for index, chunk in enumerate(chunks, start=1):
                context.append(
                    f"[资料 {index}]\n"
                    f"内容：{chunk['content']}\n"
                    f"相关度：{chunk['score']}"
                )

            return "\n\n".join(context)

        return [search_knowledge_base]

    def build_graph(
        self,
        *,
        session: AsyncSession,
        knowledge_base_id: UUID,
        retrieved_sources: list[dict],
        checkpointer: BaseCheckpointSaver,
    ):
        """构建带持久化记忆的 LangGraph 执行图。"""

        tools = self._build_tools(
            session=session,
            knowledge_base_id=knowledge_base_id,
            retrieved_sources=retrieved_sources,
        )

        model_with_tools = self.chat_model.bind_tools(tools)

        system_prompt = """
你是一个专业的知识库问答助手。

请遵循以下规则：

1. 用户的问题涉及知识库内容时，优先调用 search_knowledge_base 工具检索资料。
2. 必须根据检索到的资料回答，不要编造知识库中不存在的信息。
3. 如果没有检索到相关资料，明确告知用户。
4. 回答应准确、清晰、有条理。
5. 不要向用户展示内部工具调用过程。
6. 结合当前会话的历史消息理解用户的追问。
7. 如果用户使用“它”“这个”“刚才提到的”等指代，
   应结合历史消息判断其含义。
"""

        async def call_model(state: MessagesState):
            messages = state["messages"]

            if not any(isinstance(message, SystemMessage) for message in messages):
                messages = [
                    SystemMessage(content=system_prompt),
                    *messages,
                ]

            response = await model_with_tools.ainvoke(messages)
            return {"messages": [response]}

        builder = StateGraph(MessagesState)

        builder.add_node("agent", call_model)
        builder.add_node("tools", ToolNode(tools))

        builder.add_edge(START, "agent")

        builder.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: END,
            },
        )

        builder.add_edge("tools", "agent")

        return builder.compile(checkpointer=checkpointer)

    def _build_config(
        self,
        *,
        thread_id: str,
        knowledge_base_id: UUID,
        user_id: UUID,
        request_mode: str,
    ) -> dict:
        config = {
            "run_name": f"knowledge-base-agent-{request_mode}",
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "",
            },
            "recursion_limit": 10,
            "metadata": {
                "langfuse_session_id": thread_id,
                "langfuse_user_id": str(user_id),
                "langfuse_tags": [
                    "agent",
                    "rag",
                    "knowledge-base",
                ],
                "knowledge_base_id": str(knowledge_base_id),
                "request_mode": request_mode,
            },
        }

        if request_mode == "stream":
            config["metadata"]["langfuse_tags"].append("stream")

        if settings.LANGFUSE_TRACING_ENABLED:
            config["callbacks"] = [CallbackHandler()]

        return config

    async def stream(
        self,
        *,
        session: AsyncSession,
        knowledge_base_id: UUID,
        user_id: UUID,
        query: str,
        thread_id: str,
        checkpointer: BaseCheckpointSaver,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式执行支持多轮会话记忆的 Agent。"""

        if not query.strip():
            raise ValueError("Query cannot be empty")

        retrieved_sources: list[dict] = []

        graph = self.build_graph(
            session=session,
            knowledge_base_id=knowledge_base_id,
            retrieved_sources=retrieved_sources,
            checkpointer=checkpointer,
        )

        answer_parts: list[str] = []

        yield {"event": "start", "data": {}}

        async for part in graph.astream(
            {"messages": [("human", query)]},
            config=self._build_config(
                thread_id=thread_id,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                request_mode="stream",
            ),
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            if part["type"] == "messages":
                message_chunk, metadata = part["data"]

                if metadata.get("langgraph_node") != "agent":
                    continue

                if not isinstance(message_chunk, AIMessageChunk):
                    continue

                # 只输出文本，不把工具调用参数发送给前端。
                content = message_chunk.text

                if not isinstance(content, str) or not content:
                    continue

                answer_parts.append(content)

                yield {
                    "event": "token",
                    "data": {"content": content},
                }

            elif part["type"] == "updates":
                updates = part["data"]

                if "tools" not in updates:
                    continue

                tool_messages = updates["tools"].get("messages", [])

                for message in tool_messages:
                    yield {
                        "event": "tool_end",
                        "data": {
                            "tool": getattr(message, "name", "unknown"),
                            "tool_call_id": getattr(
                                message,
                                "tool_call_id",
                                None,
                            ),
                            "status": "success",
                        },
                    }

        yield {
            "event": "done",
            "data": {
                "answer": "".join(answer_parts),
                "sources": retrieved_sources,
            },
        }

    async def ask(
        self,
        *,
        session: AsyncSession,
        knowledge_base_id: UUID,
        user_id: UUID,
        query: str,
        thread_id: str,
        checkpointer: BaseCheckpointSaver,
    ) -> dict:
        """执行一次支持多轮会话记忆的 Agent 对话。"""

        if not query.strip():
            raise ValueError("Query cannot be empty")

        retrieved_sources: list[dict] = []

        graph = self.build_graph(
            session=session,
            knowledge_base_id=knowledge_base_id,
            retrieved_sources=retrieved_sources,
            checkpointer=checkpointer,
        )

        result = await graph.ainvoke(
            {"messages": [("human", query)]},
            config=self._build_config(
                thread_id=thread_id,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                request_mode="ask",
            ),
        )

        final_message = result["messages"][-1]
        answer = final_message.content

        if not isinstance(answer, str):
            answer = json.dumps(answer, ensure_ascii=False)

        return {
            "answer": answer,
            "sources": retrieved_sources,
        }


agent_service = AgentService()

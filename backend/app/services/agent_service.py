import asyncio
import json
import logging
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
from app.services.retrieval_service import RetrievalServiceError, retrieve_chunks

logger = logging.getLogger(__name__)


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
        on_retry=None,
    ):
        """创建绑定当前请求上下文的异步工具。"""

        @tool
        async def search_knowledge_base(query: str) -> str:
            """搜索当前知识库，获取与用户问题相关的资料。"""
            try:
                chunks = await retrieve_chunks(
                    session=session,
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    limit=5,
                    on_retry=on_retry,
                )
            except RetrievalServiceError as exc:
                return (
                    "【工具暂时不可用】"
                    f"错误代码：{exc.code}。原因：{exc.message} "
                    "本次检索没有成功，不能将其解释为知识库没有相关资料。"
                    "请向用户说明检索暂时不可用，不要编造检索结果。"
                )

            existing_ids = {item["chunk_id"] for item in retrieved_sources}
            for chunk in chunks:
                if chunk["chunk_id"] not in existing_ids:
                    retrieved_sources.append(chunk)
                    existing_ids.add(chunk["chunk_id"])

            if not chunks:
                return (
                    "知识库检索成功，但没有找到相关资料。"
                    "请如实告知用户没有检索到相关内容。"
                )

            return "\n\n".join(
                f"[资料 {index}]\n内容：{chunk['content']}\n相关度：{chunk['score']}"
                for index, chunk in enumerate(chunks, start=1)
            )

        return [search_knowledge_base]

    def build_graph(
        self,
        *,
        session: AsyncSession,
        knowledge_base_id: UUID,
        retrieved_sources: list[dict],
        checkpointer: BaseCheckpointSaver,
        on_retry=None,
    ):
        tools = self._build_tools(
            session=session,
            knowledge_base_id=knowledge_base_id,
            retrieved_sources=retrieved_sources,
            on_retry=on_retry,
        )
        model_with_tools = self.chat_model.bind_tools(tools)

        system_prompt = """
你是一个专业的知识库问答助手。
1. 用户问题涉及知识库内容时，优先调用 search_knowledge_base。
2. 必须根据检索资料回答，不要编造知识库中不存在的信息。
3. 检索成功但没有结果时，明确告知用户。
4. 工具暂时不可用时，不能将其解释为知识库没有相关资料。
5. 工具参数错误时，检查参数并在合理范围内修正后重试；不要无限重复相同调用。
6. 回答准确、清晰、有条理，不向用户展示内部工具调用过程。
7. 结合当前会话历史理解用户追问和指代。
"""

        async def call_model(state: MessagesState):
            messages = state["messages"]
            if not any(isinstance(message, SystemMessage) for message in messages):
                messages = [SystemMessage(content=system_prompt), *messages]
            response = await model_with_tools.ainvoke(messages)
            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("agent", call_model)
        builder.add_node("tools", ToolNode(tools))
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent", tools_condition, {"tools": "tools", END: END}
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
            "configurable": {"thread_id": thread_id, "checkpoint_ns": ""},
            "recursion_limit": 10,
            "metadata": {
                "langfuse_session_id": thread_id,
                "langfuse_user_id": str(user_id),
                "langfuse_tags": ["agent", "rag", "knowledge-base"],
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
        """流式执行 Agent，并实时转发工具重试事件。"""
        if not query.strip():
            raise ValueError("Query cannot be empty")

        retrieved_sources: list[dict] = []
        event_queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_retry(attempt: int, exc: Exception, delay: float, service: str):
            event = {
                "event": "tool_retry",
                "data": {
                    "tool": "search_knowledge_base",
                    "service": service,
                    "attempt": attempt,
                    "delay": round(delay, 2),
                    "message": f"{service} 服务暂时异常，正在重试。",
                },
            }
            loop.call_soon_threadsafe(event_queue.put_nowait, ("retry", event))

        graph = self.build_graph(
            session=session,
            knowledge_base_id=knowledge_base_id,
            retrieved_sources=retrieved_sources,
            checkpointer=checkpointer,
            on_retry=on_retry,
        )
        config = self._build_config(
            thread_id=thread_id,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            request_mode="stream",
        )

        async def produce_graph():
            try:
                async for part in graph.astream(
                    {"messages": [("human", query)]},
                    config=config,
                    stream_mode=["messages", "updates"],
                    version="v2",
                ):
                    await event_queue.put(("graph_part", part))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await event_queue.put(("graph_error", exc))
            finally:
                await event_queue.put(("graph_finished", None))

        answer_parts: list[str] = []
        yield {"event": "start", "data": {}}
        producer = asyncio.create_task(produce_graph())

        try:
            finished = False
            while not finished:
                kind, payload = await event_queue.get()

                if kind == "retry":
                    yield payload
                    continue
                if kind == "graph_error":
                    raise payload
                if kind == "graph_finished":
                    finished = True
                    continue

                part = payload
                if part["type"] == "messages":
                    message_chunk, metadata = part["data"]
                    if metadata.get("langgraph_node") != "agent":
                        continue
                    if not isinstance(message_chunk, AIMessageChunk):
                        continue
                    content = message_chunk.text
                    if isinstance(content, str) and content:
                        answer_parts.append(content)
                        yield {"event": "token", "data": {"content": content}}

                elif part["type"] == "updates":
                    updates = part["data"]
                    if "agent" in updates:
                        for message in updates["agent"].get("messages", []):
                            for tool_call in getattr(message, "tool_calls", []):
                                yield {
                                    "event": "tool_start",
                                    "data": {
                                        "tool": tool_call.get("name", "unknown"),
                                        "tool_call_id": tool_call.get("id"),
                                    },
                                }

                    if "tools" in updates:
                        for message in updates["tools"].get("messages", []):
                            content = message.content
                            degraded = (
                                isinstance(content, str)
                                and content.startswith("【工具暂时不可用】")
                            )
                            status = (
                                "degraded" if degraded
                                else getattr(message, "status", "success")
                            )
                            yield {
                                "event": "tool_end",
                                "data": {
                                    "tool": getattr(message, "name", "unknown"),
                                    "tool_call_id": getattr(message, "tool_call_id", None),
                                    "status": status,
                                    "error": str(content) if degraded or status == "error" else None,
                                },
                            }

            await producer
            yield {
                "event": "done",
                "data": {
                    "answer": "".join(answer_parts),
                    "sources": retrieved_sources,
                },
            }
        finally:
            if not producer.done():
                producer.cancel()
                try:
                    await producer
                except asyncio.CancelledError:
                    pass

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
        answer = result["messages"][-1].content
        if not isinstance(answer, str):
            answer = json.dumps(answer, ensure_ascii=False)
        return {"answer": answer, "sources": retrieved_sources}


agent_service = AgentService()

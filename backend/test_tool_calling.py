
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from app.core.config import settings


@tool
def search_knowledge_base(query: str) -> str:
    """搜索知识库，获取与用户问题相关的资料。"""
    return f"知识库检索测试结果：找到了与「{query}」相关的资料。"


chat_model = init_chat_model(
    model=settings.BAIYOU_MODEL,
    model_provider="openai",
    base_url=settings.BAIYOU_BASE_URL,
    api_key=settings.BAIYOU_API_KEY,
    temperature=0.2,
    max_retries=2,
    timeout=60,
)

model_with_tools = chat_model.bind_tools([search_knowledge_base])

response = model_with_tools.invoke(
    "请使用 search_knowledge_base 工具搜索：RAG 的工作原理。"
)

print("模型响应：")
print(response)

print("\n工具调用：")
print(response.tool_calls)

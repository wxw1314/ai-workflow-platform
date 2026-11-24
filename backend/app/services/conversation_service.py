from uuid import UUID


def build_conversation_thread_id(
    *,
    owner_id: UUID,
    knowledge_base_id: UUID,
    conversation_id: UUID,
) -> str:
    """
    构造 LangGraph Checkpointer 使用的 thread_id。

    同一个用户、知识库和会话组合，
    始终对应唯一的 LangGraph thread。
    """
    return (
        f"user:{owner_id}:"
        f"kb:{knowledge_base_id}:"
        f"session:{conversation_id}"
    )

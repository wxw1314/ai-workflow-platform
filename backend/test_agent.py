from uuid import UUID

from sqlmodel import Session

from app.core.db import engine
from app.services.agent_service import agent_service


# 替换成你数据库中真实存在的知识库 ID
KNOWLEDGE_BASE_ID = UUID("4aec4c18-56cb-41e9-bb5c-9edd1d6467ef")


with Session(engine) as session:
    result = agent_service.ask(
        session=session,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        query="请介绍一下这个知识库中的主要内容。",
    )

    print("\n===== Agent 回答 =====")
    print(result["answer"])

    print("\n===== 引用来源 =====")
    for source in result["sources"]:
        print(source)
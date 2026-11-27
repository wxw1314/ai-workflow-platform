
from sqlmodel import Session

from app.core.db import engine
from app.services.rag_service import rag_service


def main() -> None:
    # 替换成你自己的知识库 UUID
    knowledge_base_id = "4aec4c18-56cb-41e9-bb5c-9edd1d6467ef"

    # 测试问题
    query = "请总结这个知识库中的主要内容"

    with Session(engine) as session:
        print("=" * 60)
        print("开始测试 RAG 问答")
        print("=" * 60)

        print(f"\n用户问题：{query}")
        print(f"知识库 ID：{knowledge_base_id}")

        # 执行 RAG
        result = rag_service.ask(
            session=session,
            query=query,
            knowledge_base_id=knowledge_base_id,
            limit=5,
        )

        # 输出 AI 答案
        print("\n" + "=" * 60)
        print("AI 生成的答案")
        print("=" * 60)
        print(result["answer"])

        # 输出引用来源
        print("\n" + "=" * 60)
        print(f"检索到的引用来源（共 {len(result['sources'])} 条）")
        print("=" * 60)

        for index, source in enumerate(result["sources"], start=1):
            print(f"\n--- 来源 {index} ---")
            print(f"Chunk ID: {source['chunk_id']}")
            print(f"Document ID: {source['document_id']}")
            print(f"相似度分数: {source['score']}")
            print(f"文本内容:\n{source['content']}")

        print("\n" + "=" * 60)
        print("RAG 测试完成")
        print("=" * 60)


if __name__ == "__main__":
    main()

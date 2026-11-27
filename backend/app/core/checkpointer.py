
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings


class CheckpointerManager:
    """管理 LangGraph PostgreSQL 异步 Checkpointer 的生命周期。"""

    def __init__(self) -> None:
        self.pool: AsyncConnectionPool | None = None
        self.checkpointer: AsyncPostgresSaver | None = None

    async def initialize(self) -> None:
        """创建异步连接池并初始化 Checkpointer。"""

        if self.checkpointer is not None:
            return

        conninfo = str(settings.DATABASE_URL).replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )

        pool = AsyncConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=5,
            timeout=30,
            max_waiting=10,
            max_lifetime=1800,
            max_idle=300,
            reconnect_timeout=30,
            check=AsyncConnectionPool.check_connection,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 3,
            },
            open=False,
        )

        try:
            await pool.open(wait=True, timeout=30)

            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()

            self.pool = pool
            self.checkpointer = checkpointer

        except Exception:
            await pool.close()
            raise

    async def close(self) -> None:
        """异步关闭连接池，释放数据库连接。"""

        if self.pool is not None:
            await self.pool.close()

        self.pool = None
        self.checkpointer = None


checkpointer_manager = CheckpointerManager()

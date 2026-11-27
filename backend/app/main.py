from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from langfuse import Langfuse, get_client
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.checkpointer import checkpointer_manager
from app.core.config import settings
from app.core.db import async_engine

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route):
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化 Langfuse
    if settings.LANGFUSE_TRACING_ENABLED:
        Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            base_url=settings.LANGFUSE_BASE_URL,
            tracing_enabled=True,
        )
        app.state.langfuse = get_client()
    else:
        app.state.langfuse = None

    # 初始化 Checkpointer
    await checkpointer_manager.initialize()
    app.state.checkpointer = checkpointer_manager.checkpointer

    try:
        yield
    finally:
        # 关闭 Checkpointer
        await checkpointer_manager.close()

        # 释放 Langfuse 后台资源，并发送剩余 Trace
        if app.state.langfuse is not None:
            app.state.langfuse.shutdown()

        # 释放数据库连接
        await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

app.frontend("/", directory=FRONTEND_DIR)

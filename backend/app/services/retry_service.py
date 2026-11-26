import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TypeVar

from openai import RateLimitError
from sqlalchemy.exc import DBAPIError

T = TypeVar("T")


def is_retryable_database_error(exc: Exception) -> bool:
    """只对明确的瞬时 PostgreSQL 连接/事务错误重试。"""
    current: BaseException | None = exc
    seen: set[int] = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))

        if isinstance(current, DBAPIError) and current.connection_invalidated:
            return True

        sqlstate = (
            getattr(current, "sqlstate", None)
            or getattr(current, "pgcode", None)
        )
        if isinstance(sqlstate, str):
            if sqlstate.startswith("08") or sqlstate in {"40001", "40P01"}:
                return True

        if isinstance(current, (TimeoutError, ConnectionError)):
            return True

        name = type(current).__name__
        if name in {
            "ConnectionDoesNotExist",
            "AdminShutdown",
            "CrashShutdown",
            "CannotConnectNow",
            "ConnectionFailure",
            "OperationalError",
            "InterfaceError",
        }:
            # DBAPI OperationalError / InterfaceError 只有明确断连或 SQLSTATE
            # 才会在上面的判断中命中；这里不按类名盲目重试。
            if not isinstance(current, DBAPIError):
                return True

        current = getattr(current, "__cause__", None) or getattr(
            current, "__context__", None
        )

    return False


def is_retryable_network_error(exc: Exception) -> bool:
    """判断 HTTP、网络、Milvus/gRPC 等瞬时错误。"""
    if isinstance(exc, RateLimitError):
        return True

    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    if is_retryable_database_error(exc):
        return True

    retryable_names = {
        "ConnectError", "ConnectTimeout", "ReadTimeout", "WriteTimeout",
        "PoolTimeout", "MilvusUnavailableError", "MilvusTimeoutError",
        "ConnectionFailure", "ServiceUnavailable",
    }
    if type(exc).__name__ in retryable_names:
        return True

    code_method = getattr(exc, "code", None)
    if callable(code_method):
        try:
            code = code_method()
            code_name = getattr(code, "name", str(code))
            if code_name in {
                "UNAVAILABLE", "DEADLINE_EXCEEDED", "RESOURCE_EXHAUSTED"
            }:
                return True
        except Exception:
            pass

    return False


def get_retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None

    value = headers.get("retry-after")
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        pass

    try:
        retry_time = parsedate_to_datetime(value)
        if retry_time.tzinfo is None:
            retry_time = retry_time.replace(tzinfo=timezone.utc)
        return max(
            0.0,
            (retry_time - datetime.now(timezone.utc)).total_seconds(),
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _get_retry_delay(
    attempt: int, exc: Exception, base_delay: float, max_delay: float
) -> float:
    retry_after = get_retry_after_seconds(exc)
    if retry_after is not None:
        return min(retry_after, max_delay)

    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    return min(delay + random.uniform(0, delay * 0.2), max_delay)


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 4.0,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    retry_if: Callable[[Exception], bool] | None = None,
) -> T:
    """异步有限重试；max_attempts 包含首次执行。"""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    should_retry = retry_if or is_retryable_network_error
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_attempts or not should_retry(exc):
                raise
            delay = _get_retry_delay(attempt, exc, base_delay, max_delay)
            if on_retry:
                on_retry(attempt, exc, delay)
            await asyncio.sleep(delay)

    raise RuntimeError("Unreachable retry state")


def retry_sync(
    operation: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 4.0,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    retry_if: Callable[[Exception], bool] | None = None,
) -> T:
    """同步有限重试；max_attempts 包含首次执行。"""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    should_retry = retry_if or is_retryable_network_error
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt >= max_attempts or not should_retry(exc):
                raise
            delay = _get_retry_delay(attempt, exc, base_delay, max_delay)
            if on_retry:
                on_retry(attempt, exc, delay)
            time.sleep(delay)

    raise RuntimeError("Unreachable retry state")

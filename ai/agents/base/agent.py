"""Generic asynchronous agent contract and standardized execution wrapper."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

from ai.config.logging import get_logger
from ai.schemas.common import AgentError, AgentExecutionMetadata, AgentResult
from ai.schemas.enums import ErrorCode
from ai.utils.exceptions import AppError
from ai.utils.time import MonotonicTimer

InputT = TypeVar("InputT", contravariant=True)
OutputT = TypeVar("OutputT", covariant=True)
RunInputT = TypeVar("RunInputT")
RunOutputT = TypeVar("RunOutputT")


class Agent(Protocol[InputT, OutputT]):
    """Structural interface implemented by every specialized agent."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    async def run(self, request: InputT) -> OutputT: ...


async def execute_agent(
    agent: Agent[RunInputT, RunOutputT],
    request: RunInputT,
) -> AgentResult[RunOutputT]:
    """Execute an agent and convert expected failures to a typed result envelope."""

    timer = MonotonicTimer()
    logger = get_logger(agent.name)
    try:
        output = await agent.run(request)
        metadata = AgentExecutionMetadata(
            agent_name=agent.name,
            agent_version=agent.version,
            duration_ms=timer.elapsed_milliseconds,
        )
        logger.info("agent_completed", duration_ms=metadata.duration_ms)
        return AgentResult(output=output, metadata=metadata)
    except AppError as exc:
        logger.warning("agent_failed", error_code=exc.code, retryable=exc.retryable)
        return AgentResult(
            error=AgentError(
                code=exc.code,
                message=exc.public_message,
                retryable=exc.retryable,
                agent_name=agent.name,
            ),
            metadata=AgentExecutionMetadata(
                agent_name=agent.name,
                agent_version=agent.version,
                duration_ms=timer.elapsed_milliseconds,
            ),
        )
    except Exception:
        logger.exception("agent_failed_unexpectedly")
        return AgentResult(
            error=AgentError(
                code=ErrorCode.INTERNAL_ERROR,
                message="The agent could not complete its task.",
                retryable=False,
                agent_name=agent.name,
            ),
            metadata=AgentExecutionMetadata(
                agent_name=agent.name,
                agent_version=agent.version,
                duration_ms=timer.elapsed_milliseconds,
            ),
        )


AgentCallable = Callable[[RunInputT], Awaitable[RunOutputT]]

__all__ = ["Agent", "AgentCallable", "execute_agent"]

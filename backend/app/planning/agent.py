"""A bounded agent with one read-only catalog tool."""

import asyncio
import json

import httpx
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain.tools import tool
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from openai import APITimeoutError
from pydantic import ValidationError as PydanticValidationError

from app.catalog.service import list_attractions
from app.config import Settings, get_settings
from app.contracts import AgentCandidate, GenerationRequest
from app.errors import (
    AgentInvalidOutput,
    AgentLimitExceeded,
    AgentTimeout,
    AgentUnavailable,
    AppError,
)

SYSTEM_PROMPT = """你是旅游行程规划助手。必须先调用一次 search_attractions 查询用户指定城市。
只使用工具返回的景点 ID，按用户天数安排，每天最多两个，整份行程不得重复景点。
不编造景点或价格。景点不足时允许部分日期为空。最终只输出 JSON 对象，格式为：
{"days":[{"day":1,"attraction_ids":["景点ID"]}]}。每一天都必须出现，不要包含其他字段、代码块或解释。
"""


def _build_chat_model(settings: Settings) -> ChatOpenAI:
    if not settings.llm_model.strip() or not settings.llm_api_key.get_secret_value().strip():
        raise AgentUnavailable("未配置模型名称或密钥，请先配置模型服务。")
    return ChatOpenAI(
        model=settings.llm_model.strip(),
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url.strip() or None,
        timeout=settings.agent_timeout_seconds,
        max_retries=0,
    )


async def generate_candidate(request: GenerationRequest) -> AgentCandidate:
    """Ask the configured model to query once and return a validated ID-only draft."""
    settings = get_settings()
    try:
        model = _build_chat_model(settings)
    except AppError:
        raise
    except Exception as exc:
        raise AgentUnavailable() from exc
    found_ids: set[str] = set()
    call_count = 0

    @tool
    async def search_attractions(city: str) -> str:
        """查询本次旅游目的地的全部示例景点，返回景点编号、类别和门票信息。"""
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise AgentLimitExceeded()
        if city.strip() != request.city:
            raise AgentInvalidOutput()
        items = list_attractions(city=request.city)
        found_ids.update(item.id for item in items)
        return json.dumps([item.model_dump() for item in items], ensure_ascii=False)

    agent = create_agent(
        model=model,
        tools=[search_attractions],
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            ModelCallLimitMiddleware(run_limit=2, exit_behavior="error"),
            ToolCallLimitMiddleware(run_limit=1, exit_behavior="error"),
        ],
    )
    user_input = request.model_dump(exclude={"mode"})
    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {
                    "messages": [
                        {"role": "user", "content": json.dumps(user_input, ensure_ascii=False)}
                    ]
                }
            ),
            timeout=settings.agent_timeout_seconds,
        )
    except (ModelCallLimitExceededError, ToolCallLimitExceededError) as exc:
        raise AgentLimitExceeded() from exc
    except (TimeoutError, APITimeoutError, httpx.TimeoutException) as exc:
        raise AgentTimeout() from exc
    except AppError:
        raise
    except Exception as exc:
        # Do not expose provider response bodies, request headers or API keys.
        raise AgentUnavailable() from exc

    messages = result.get("messages", [])
    if call_count != 1 or not messages or not isinstance(messages[-1], AIMessage):
        raise AgentInvalidOutput()
    try:
        candidate = AgentCandidate.model_validate_json(messages[-1].text)
    except (PydanticValidationError, ValueError, TypeError) as exc:
        raise AgentInvalidOutput() from exc

    used_ids = [attraction_id for day in candidate.days for attraction_id in day.attraction_ids]
    if any(attraction_id not in found_ids for attraction_id in used_ids):
        raise AgentInvalidOutput()
    if len(used_ids) != len(set(used_ids)):
        raise AgentInvalidOutput()
    return candidate

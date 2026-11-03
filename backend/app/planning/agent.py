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

SYSTEM_PROMPT = """你是汕头旅游行程规划助手。必须先调用一次 search_attractions 查询汕头景点。
只使用工具返回的景点 ID，按用户天数、偏好和门票预算安排，每天最多两个，整份行程不得重复景点。
尽量将相近区域放在同一天，南澳岛不和其他区域安排在同一天，每天参考游览时长合计不超过 480 分钟。
每天的 note 简要说明顺序、建议时段与安排理由；资料不足或预算可能不够应如实说明。
参考价格可能未知，不要编造价格、实际开放时间、实时路况或精确交通时间。
景点不足时允许部分日期为空。最终只输出 JSON 对象，格式为：
{"days":[{"day":1,"attraction_ids":["景点ID"],"note":"建议上午游览，预留交通时间。"}]}。
每一天都必须出现，不要包含其他字段或代码块。
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
    found_catalog = {}
    call_count = 0

    @tool
    async def search_attractions(city: str) -> str:
        """查询汕头景点参考资料，包括区域、建议时长及已知的参考门票。"""
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise AgentLimitExceeded()
        if city.strip() != request.city:
            raise AgentInvalidOutput()
        items = list_attractions(city=request.city)
        found_catalog.update({item.id: item for item in items})
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
    if any(attraction_id not in found_catalog for attraction_id in used_ids):
        raise AgentInvalidOutput()
    if len(used_ids) != len(set(used_ids)):
        raise AgentInvalidOutput()
    if [day.day for day in candidate.days] != list(range(1, request.day_count + 1)):
        raise AgentInvalidOutput()
    for day in candidate.days:
        if day.attraction_ids and not (day.note and day.note.strip()):
            raise AgentInvalidOutput()
        if len(day.attraction_ids) > 2:
            raise AgentInvalidOutput()
        items = [found_catalog[item_id] for item_id in day.attraction_ids]
        if sum(item.duration_min or 0 for item in items) > 480:
            raise AgentInvalidOutput()
        if any(item.area == "南澳" for item in items) and any(
            item.area != "南澳" for item in items
        ):
            raise AgentInvalidOutput()
    return candidate

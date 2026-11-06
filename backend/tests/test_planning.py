import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import SecretStr

from app.catalog.service import get_catalog
from app.config import Settings
from app.contracts import CandidateDay, GenerationRequest, PlanDay, PlanInput, PlanView
from app.errors import (
    AgentInvalidOutput,
    AgentLimitExceeded,
    AgentTimeout,
    AgentUnavailable,
    ServiceNotReady,
    ValidationError,
)
from app.main import app
from app.planning import agent, service


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, **kwargs)


def model_call(city="汕头", call_id="tool-1"):
    return {
        "name": "search_attractions",
        "args": {"city": city},
        "id": call_id,
        "type": "tool_call",
    }


def request(mode="agent"):
    return GenerationRequest(
        city="汕头", day_count=1, preferences=["自然"], budget_cny=50, mode=mode
    )


def final_message(ids=None):
    return AIMessage(
        content=json.dumps(
            {"days": [{"day": 1, "attraction_ids": ids or ["st-001"], "note": "建议上午游览。"}]}
        )
    )


@pytest.fixture
def configured(monkeypatch):
    settings = Settings(_env_file=None, llm_model="test-model", llm_api_key=SecretStr("test-key"))
    monkeypatch.setattr(agent, "get_settings", lambda: settings)
    return settings


def use_model(monkeypatch, responses):
    model = ScriptedModel(responses=responses)
    monkeypatch.setattr(agent, "_build_chat_model", lambda _settings: model)
    return model


def test_real_agent_loop_queries_tool_once_and_returns_candidate(configured, monkeypatch):
    calls = []
    original = agent.list_attractions

    def record_query(*args, **kwargs):
        calls.append(kwargs.get("city"))
        return original(*args, **kwargs)

    monkeypatch.setattr(agent, "list_attractions", record_query)
    use_model(monkeypatch, [AIMessage(content="", tool_calls=[model_call()]), final_message()])
    candidate = asyncio.run(agent.generate_candidate(request()))
    assert candidate.days[0].attraction_ids == ["st-001"]
    assert candidate.days[0].note == "建议上午游览。"
    assert calls == ["汕头"]


@pytest.mark.parametrize(
    "responses",
    [
        [final_message()],
        [AIMessage(content="", tool_calls=[model_call()]), final_message(["missing-001"])],
        [AIMessage(content="", tool_calls=[model_call()]), final_message(["st-001", "st-001"])],
        [AIMessage(content="", tool_calls=[model_call()]), final_message(["st-008", "st-001"])],
        [
            AIMessage(content="", tool_calls=[model_call()]),
            AIMessage(content='{"days":[{"day":2,"attraction_ids":["st-001"],"note":"上午"}]}'),
        ],
        [
            AIMessage(content="", tool_calls=[model_call()]),
            AIMessage(content='{"days":[{"day":1,"attraction_ids":["st-001"]}]}'),
        ],
        [AIMessage(content="", tool_calls=[model_call()]), AIMessage(content="not-json")],
        [AIMessage(content="", tool_calls=[model_call("泉州")]), final_message()],
    ],
)
def test_agent_rejects_missing_tool_wrong_city_invalid_ids_and_output(
    configured, monkeypatch, responses
):
    use_model(monkeypatch, responses)
    with pytest.raises(AgentInvalidOutput):
        asyncio.run(agent.generate_candidate(request()))


def test_parallel_tool_calls_are_rejected_before_execution(configured, monkeypatch):
    calls = []
    monkeypatch.setattr(agent, "list_attractions", lambda **kwargs: calls.append(kwargs))
    use_model(
        monkeypatch,
        [AIMessage(content="", tool_calls=[model_call(call_id="a"), model_call(call_id="b")])],
    )
    with pytest.raises(AgentLimitExceeded):
        asyncio.run(agent.generate_candidate(request()))
    assert calls == []


def test_repeated_tool_call_is_limited(configured, monkeypatch):
    use_model(
        monkeypatch,
        [
            AIMessage(content="", tool_calls=[model_call()]),
            AIMessage(content="", tool_calls=[model_call(call_id="b")]),
        ],
    )
    with pytest.raises(AgentLimitExceeded):
        asyncio.run(agent.generate_candidate(request()))


def test_agent_timeout_cancels_async_request(monkeypatch):
    cancelled = []

    class SlowModel(ScriptedModel):
        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                cancelled.append(True)
                raise
            return self._generate(messages, stop=stop, **kwargs)

    settings = Settings(
        _env_file=None, llm_model="test", llm_api_key=SecretStr("test"), agent_timeout_seconds=0.01
    )
    monkeypatch.setattr(agent, "get_settings", lambda: settings)
    monkeypatch.setattr(
        agent, "_build_chat_model", lambda _settings: SlowModel(responses=[final_message()])
    )
    with pytest.raises(AgentTimeout):
        asyncio.run(agent.generate_candidate(request()))
    assert cancelled == [True]


def test_missing_model_configuration_is_reported(monkeypatch):
    monkeypatch.setattr(
        agent,
        "get_settings",
        lambda: Settings(_env_file=None, llm_model="", llm_api_key=SecretStr("")),
    )
    with pytest.raises(AgentUnavailable):
        asyncio.run(agent.generate_candidate(request()))


def test_model_adapter_disables_retries_and_accepts_compatible_endpoint():
    settings = Settings(
        _env_file=None,
        llm_model="test-model",
        llm_api_key=SecretStr("test-key"),
        llm_base_url="https://example.invalid/v1",
    )
    model = agent._build_chat_model(settings)
    assert model.max_retries == 0
    assert model.openai_api_base == "https://example.invalid/v1"


def test_model_errors_are_sanitized(configured, monkeypatch):
    class FailingModel(ScriptedModel):
        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("sensitive-test-value")

    monkeypatch.setattr(
        agent, "_build_chat_model", lambda _settings: FailingModel(responses=[final_message()])
    )
    with pytest.raises(AgentUnavailable) as exc:
        asyncio.run(agent.generate_candidate(request()))
    assert "sensitive-test-value" not in str(exc.value)


def sample_plan(draft):
    attraction = get_catalog()["st-001"]
    return PlanView(
        **draft.model_dump(exclude={"days"}),
        days=[PlanDay(day=1, attractions=[attraction], subtotal_cny=0)],
        total_cny=0,
        over_budget=False,
        warnings=["费用仅包含示例景点门票。"],
    )


def test_rule_endpoint_uses_member_a_services_without_agent(monkeypatch):
    def make_rule_candidate(input_request):
        return PlanInput(
            **input_request.model_dump(), days=[CandidateDay(day=1, attraction_ids=["st-001"])]
        )

    monkeypatch.setattr(
        service, "get_itinerary_services", lambda: (make_rule_candidate, sample_plan)
    )
    monkeypatch.setattr(
        service, "generate_candidate", lambda _request: pytest.fail("Agent must not run")
    )
    with TestClient(app) as client:
        response = client.post("/api/plans/generate", json=request("rules").model_dump())
    assert response.status_code == 200
    assert response.json()["mode"] == "rules"
    assert response.json()["total_cny"] == 0


def test_missing_a_service_is_clear_and_invalid_input_is_422(monkeypatch):
    def not_ready():
        raise ServiceNotReady()

    monkeypatch.setattr(service, "get_itinerary_services", not_ready)
    with TestClient(app) as client:
        not_ready = client.post("/api/plans/generate", json=request("rules").model_dump())
        bad_city = client.post(
            "/api/plans/generate", json={**request("rules").model_dump(), "city": "不存在"}
        )
    assert not_ready.status_code == 503
    assert not_ready.json()["code"] == "SERVICE_NOT_READY"
    assert bad_city.status_code == 422
    assert bad_city.json()["code"] == "VALIDATION_ERROR"


def test_agent_candidate_business_failure_maps_to_invalid_output(monkeypatch):
    async def candidate(_request):
        return agent.AgentCandidate(days=[CandidateDay(day=1, attraction_ids=["st-001"])])

    def reject(_draft):
        raise ValidationError("not valid")

    monkeypatch.setattr(service, "get_itinerary_services", lambda: (lambda _: None, reject))
    monkeypatch.setattr(service, "generate_candidate", candidate)
    with TestClient(app) as client:
        response = client.post("/api/plans/generate", json=request().model_dump())
    assert response.status_code == 502
    assert response.json()["code"] == "AGENT_INVALID_OUTPUT"

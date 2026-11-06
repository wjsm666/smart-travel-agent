"""Integration checks for the first member's minimal generation flow."""

import pytest
from fastapi.testclient import TestClient

from app.catalog import service as catalog_service
from app.contracts import Attraction, CandidateDay, GenerationRequest, PlanInput
from app.errors import ValidationError
from app.itineraries import service as itinerary_service
from app.itineraries.rules import make_rule_candidate
from app.itineraries.service import validate_and_enrich
from app.main import app
from app.planning import service as planning_service


@pytest.fixture
def catalog(monkeypatch):
    def item(item_id, category="自然", price=10, area="市区", duration=120):
        return Attraction(
            id=item_id,
            city="汕头",
            name=item_id,
            category=category,
            description="独立测试资料",
            ticket_cny=price,
            area=area,
            duration_min=duration,
        )

    items = [
        item("a", "人文", 20),
        item("b", price=None),
        item("c", area="南澳", duration=360),
        item("d", area="南澳", duration=360),
        item("e", price=30),
    ]
    monkeypatch.setattr(catalog_service, "get_catalog", lambda: {i.id: i for i in items})
    monkeypatch.setattr(itinerary_service, "get_catalog", lambda: {i.id: i for i in items})
    return items


def request(**changes):
    return GenerationRequest(
        **{
            "city": "汕头",
            "day_count": 2,
            "preferences": ["自然"],
            "budget_cny": 25,
            "mode": "rules",
            **changes,
        }
    )


def draft(ids, **changes):
    return PlanInput(
        **request(day_count=len(ids), **changes).model_dump(),
        days=[CandidateDay(day=i + 1, attraction_ids=items) for i, items in enumerate(ids)],
    )


def test_rule_endpoint_is_connected_deterministic_and_does_not_call_agent(catalog, monkeypatch):
    monkeypatch.setattr(
        planning_service, "generate_candidate", lambda _: pytest.fail("rules called Agent")
    )
    with TestClient(app) as client:
        first = client.post("/api/plans/generate", json=request().model_dump())
        second = client.post("/api/plans/generate", json=request().model_dump())
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "draft"
    assert first.json()["days"][0]["attractions"][0]["id"] == "b"
    ids = [i["id"] for d in first.json()["days"] for i in d["attractions"]]
    assert len(ids) == len(set(ids))


def test_unknown_prices_and_known_over_budget_are_distinct(catalog):
    unknown = validate_and_enrich(draft([["b"]]))
    assert unknown.total_cny == 0
    assert unknown.has_unknown_prices and unknown.over_budget is None
    exceeded = validate_and_enrich(draft([["b", "e"]]))
    assert exceeded.total_cny == 30
    assert exceeded.over_budget is True
    assert exceeded.warnings


@pytest.mark.parametrize(
    "ids",
    [
        [["missing"]],
        [["a"], ["a"]],
        [["a", "b", "e"]],
        [["a", "c"]],
        [["c", "d"]],
    ],
)
def test_invalid_candidates_are_rejected(catalog, ids):
    with pytest.raises(ValidationError):
        validate_and_enrich(draft(ids))


def test_city_and_date_structure_are_checked(catalog):
    with pytest.raises(ValidationError):
        make_rule_candidate(request(city="厦门"))
    with pytest.raises(ValidationError):
        validate_and_enrich(draft([["a"]], city="厦门"))
    invalid = draft([["a"], []])
    invalid.days.reverse()
    with pytest.raises(ValidationError):
        validate_and_enrich(invalid)


def test_validation_endpoint_uses_catalog_prices_and_preserves_note(catalog):
    value = draft([["a"]])
    value.days[0].note = "用户自己的安排"
    with TestClient(app) as client:
        response = client.post("/api/plans/validate", json=value.model_dump())
        tampered = client.post("/api/plans/validate", json={**value.model_dump(), "total_cny": 0})
    assert response.status_code == 200
    assert response.json()["total_cny"] == 20
    assert response.json()["days"][0]["note"] == "用户自己的安排"
    assert tampered.status_code == 422


def test_empty_and_non_preferred_days_are_explicit(catalog):
    empty = validate_and_enrich(draft([[], []]))
    assert any("全部为空" in w for w in empty.warnings)
    non_preferred = validate_and_enrich(draft([["a"]]))
    assert any("没有匹配" in w for w in non_preferred.warnings)


def test_agent_candidate_uses_same_enrichment(catalog, monkeypatch):
    from app.contracts import AgentCandidate

    async def candidate(_request):
        return AgentCandidate(days=[CandidateDay(day=1, attraction_ids=["a"])])

    monkeypatch.setattr(planning_service, "generate_candidate", candidate)
    with TestClient(app) as client:
        result = client.post(
            "/api/plans/generate", json=request(day_count=1, mode="agent").model_dump()
        )
    assert result.status_code == 200
    assert result.json()["total_cny"] == 20
    assert result.json()["mode"] == "agent"

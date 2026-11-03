import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from app.catalog import service
from app.config import BACKEND_DIR, Settings
from app.contracts import GenerationRequest, SavedTrip
from app.errors import StorageError
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_seed_is_unique_and_has_six_examples_per_city():
    catalog = service.get_catalog()
    assert len(catalog) == 12
    assert {item.city for item in catalog.values()} == {"厦门", "泉州"}
    for city in ("厦门", "泉州"):
        items = service.list_attractions(city=city)
        assert len(items) == 6
        assert {
            kind: sum(item.category == kind for item in items) for kind in ("自然", "人文", "休闲")
        } == {
            "自然": 2,
            "人文": 2,
            "休闲": 2,
        }


def test_health_filtering_and_empty_results(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    items = client.get("/api/attractions", params={"city": "厦门", "category": "自然"}).json()[
        "items"
    ]
    assert [item["id"] for item in items] == ["xm-001", "xm-002"]
    keyword = client.get("/api/attractions", params={"city": "厦门", "keyword": "公园"}).json()[
        "items"
    ]
    assert [item["id"] for item in keyword] == ["xm-001"]
    assert client.get("/api/attractions", params={"city": "不存在"}).json() == {"items": []}
    invalid = client.get("/api/attractions", params={"category": "未知"})
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_catalog_data_errors_do_not_overwrite_file(tmp_path, monkeypatch, client):
    path = tmp_path / "attractions.json"
    path.write_text("{broken", encoding="utf-8")
    settings = Settings(_env_file=None, attractions_path=path)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    response = client.get("/api/attractions")
    assert response.status_code == 500
    assert response.json()["code"] == "STORAGE_ERROR"
    assert path.read_text(encoding="utf-8") == "{broken"

    sample = {
        "id": "same",
        "city": "厦门",
        "name": "示例",
        "category": "自然",
        "description": "虚构",
        "ticket_cny": 2,
    }
    path.write_text(json.dumps([sample, sample], ensure_ascii=False), encoding="utf-8")
    with pytest.raises(StorageError):
        service.get_catalog()


@pytest.mark.parametrize("bad", [True, 1.5, "2", -1, 6])
def test_day_count_rejects_invalid_values(bad):
    with pytest.raises(PydanticValidationError):
        GenerationRequest(city="厦门", day_count=bad, preferences=[], budget_cny=50, mode="rules")


def test_contract_normalizes_and_rejects_extra_fields():
    request = GenerationRequest(
        city=" 厦门 ", day_count=2, preferences=[" 自然 ", "自然"], budget_cny=0, mode=" rules "
    )
    assert request.city == "厦门"
    assert request.preferences == ["自然"]
    with pytest.raises(PydanticValidationError):
        GenerationRequest(city="厦门", day_count=2, budget_cny=True, mode="rules")
    with pytest.raises(PydanticValidationError):
        GenerationRequest(city="厦门", day_count=2, budget_cny=1, mode="rules", unknown="x")


def test_settings_resolve_paths_independently_from_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None)
    assert (
        settings.resolve_data_path(settings.attractions_path)
        == BACKEND_DIR / "data/attractions.json"
    )
    assert settings.resolve_data_path(tmp_path) == tmp_path


def test_environment_takes_precedence_over_local_file(tmp_path, monkeypatch):
    config = tmp_path / ".env"
    config.write_text("LLM_MODEL=file-model\n", encoding="utf-8")
    monkeypatch.setenv("LLM_MODEL", "environment-model")
    assert Settings(_env_file=config).llm_model == "environment-model"


def test_saved_trip_requires_uuid_and_utc_timestamp():
    fields = {
        "city": "厦门",
        "day_count": 1,
        "budget_cny": 50,
        "mode": "rules",
        "days": [],
        "total_cny": 0,
        "over_budget": False,
        "warnings": [],
        "trip_id": "de305d54-75b4-431b-adb2-eb6b9e546014",
        "created_at": "2026-11-03T10:00:00Z",
    }
    assert SavedTrip(**fields).status == "saved"
    with pytest.raises(PydanticValidationError):
        SavedTrip(**{**fields, "trip_id": "not-a-uuid"})
    with pytest.raises(PydanticValidationError):
        SavedTrip(**{**fields, "created_at": "2026-11-03T10:00:00+08:00"})
    with pytest.raises(PydanticValidationError):
        SavedTrip(**{**fields, "created_at": "2026-11-03T10:00:00"})

import json

from pydantic import SecretStr

from app.config import Settings
from app.planning import agent
from app.planning.__main__ import main


def test_cli_rules_is_usable_without_model_and_returns_draft(capsys, monkeypatch):
    monkeypatch.setattr(
        agent,
        "_build_chat_model",
        lambda _: (_ for _ in ()).throw(AssertionError("model initialized")),
    )
    assert main(["--days", "2", "--preference", "自然"]) == 0
    draft = json.loads(capsys.readouterr().out)
    assert draft["mode"] == "rules" and draft["status"] == "draft"
    assert len(draft["days"]) == 2


def test_cli_invalid_request_and_missing_model_exit_with_error(capsys, monkeypatch):
    assert main(["--days", "6"]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "VALIDATION_ERROR"
    monkeypatch.setattr(
        agent,
        "get_settings",
        lambda: Settings(_env_file=None, llm_model="", llm_api_key=SecretStr("")),
    )
    assert main(["--mode", "agent"]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "AGENT_UNAVAILABLE"

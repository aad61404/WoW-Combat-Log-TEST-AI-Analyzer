"""AI generation, parsing and cleanup are exercised without external calls."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.config import settings
from app.models.schemas import CoachReport
from app.routers.demo import demo_analysis
from app.services.ai_coach import AICoach


@pytest.mark.parametrize(
    "payload", ["", "{}", "null", "[]", '{"wipe_summary":"ok"}', '{"wipe_summary":""}']
)
def test_incomplete_reports_are_rejected(payload):
    with pytest.raises(ValueError):
        AICoach()._parse_response(payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "generate", "invalid_json", "unknown_player", "cleanup"])
async def test_generation_and_fallback(monkeypatch, failure):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    payload = {
        "wipe_summary": "已記錄四次死亡，需要回顧傷害時間線。",
        "primary_causes": ["資料不足以確認因果"],
        "priority_fixes": ["回顧死前傷害"],
        "player_advice": [],
        "source": "deterministic",
    }
    if failure == "unknown_player":
        payload["player_advice"] = [{"player": "InventedPlayer", "issues": [], "suggestions": []}]
    generate = AsyncMock(
        return_value=SimpleNamespace(
            text="not json" if failure == "invalid_json" else json.dumps(payload)
        )
    )
    if failure == "generate":
        generate.side_effect = RuntimeError("secret upstream details")
    close_async = AsyncMock(side_effect=RuntimeError() if failure == "cleanup" else None)
    close_sync = Mock(side_effect=RuntimeError() if failure == "cleanup" else None)
    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate), aclose=close_async),
        close=close_sync,
    )
    monkeypatch.setattr("app.services.ai_coach.genai.Client", Mock(return_value=client))
    fixture = demo_analysis(1)
    report = await AICoach().generate_report(fixture.fight, fixture.analysis)
    assert report.source == ("ai" if failure in (None, "cleanup") else "deterministic")
    assert all(p.player != "InventedPlayer" for p in report.player_advice)
    generate.assert_awaited_once()
    close_async.assert_awaited_once()
    close_sync.assert_called_once()
    assert generate.call_args.kwargs["config"].response_schema is CoachReport

"""Offline API integration checks; no external service is called."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.ai_coach import AICoach
from app.services.wcl_client import WCLClient, WCLAPIError
from app.routers.demo import demo_analysis


def test_demo_pipeline_without_external_services(monkeypatch):
    monkeypatch.setattr(
        WCLClient, "_graphql", AsyncMock(side_effect=AssertionError("No WCL in demo"))
    )
    monkeypatch.setattr(
        AICoach, "generate_report", AsyncMock(side_effect=AssertionError("No AI in demo"))
    )
    with TestClient(app) as client:
        report = client.get("/api/demo/report")
        assert report.status_code == 200
        assert [f["id"] for f in report.json()["fights"]] == [1]
        response = client.post("/api/demo/fights/1/analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["demo"] is True
        assert data["analysis"]["total_deaths"] == 4
        assert data["coach_report"]["source"] == "deterministic"
        assert data["analysis"]["deaths"][0]["damage_taken_last_5s"]
        assert client.post("/api/demo/fights/2/analysis").status_code == 404


@pytest.mark.asyncio
async def test_missing_gemini_key_uses_summary(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(
        "app.services.ai_coach.genai.Client", Mock(side_effect=AssertionError("No client needed"))
    )
    data = demo_analysis(1)
    report = await AICoach().generate_report(data.fight, data.analysis)
    assert report.source == "deterministic"


def test_successful_fight_is_not_called_a_wipe():
    data = demo_analysis(1)
    data.fight.kill = True
    report = AICoach._build_fallback_report(data.fight, data.analysis)
    assert "擊殺成功" in report.wipe_summary
    assert "滅團，" not in report.wipe_summary


@pytest.mark.asyncio
async def test_gemini_constructor_failure_uses_summary(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        "app.services.ai_coach.genai.Client", Mock(side_effect=ValueError("Unavailable"))
    )
    data = demo_analysis(1)
    report = await AICoach().generate_report(data.fight, data.analysis)
    assert report.source == "deterministic"


@pytest.mark.asyncio
async def test_wcl_pagination_advances_and_rejects_stalled_cursor():
    data = demo_analysis(1)
    client = WCLClient()

    def page(events, next_page):
        return {
            "reportData": {
                "report": {
                    "events": {"data": events, "nextPageTimestamp": next_page},
                    "masterData": {"actors": []},
                }
            }
        }

    try:
        client._graphql = AsyncMock(
            side_effect=[page([{"timestamp": 60001}], 70000), page([{"timestamp": 70001}], None)]
        )
        events, _, _ = await client.get_fight_events("test", data.fight)
        assert len(events) == 2
        assert client._graphql.call_args_list[1].args[1]["startTime"] == 70000
        assert "$nextPage" not in client.EVENTS_QUERY
        client._graphql = AsyncMock(return_value=page([], 60000))
        with pytest.raises(WCLAPIError, match="did not advance"):
            await client.get_fight_events("test", data.fight)
    finally:
        await client.close()


def test_live_route_falls_back_and_does_not_use_demo_rules(monkeypatch):
    from app.routers.demo import demo_report, load

    report = demo_report()
    report.code = "AbCdEfGh12345678"
    raw = load("sample_events.json")
    monkeypatch.setattr(WCLClient, "get_report", AsyncMock(return_value=report))
    monkeypatch.setattr(
        WCLClient,
        "get_fight_events",
        AsyncMock(
            return_value=(
                raw["data"]["reportData"]["report"]["events"]["data"],
                report.actors,
                raw["_abilityMap"],
            )
        ),
    )
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with TestClient(app) as client:
        response = client.post(f"/api/reports/{report.code}/fights/1/analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["demo"] is False
        assert data["coach_report"]["source"] == "deterministic"
        assert data["analysis"]["total_deaths"] == 4
        assert all(e["type"] == "death" for e in data["analysis"]["evidence"])
        assert data["analysis"]["deaths"][0]["killing_blow"] == "Savage Charge"
        assert client.post(f"/api/reports/{report.code}/fights/999/analysis").status_code == 404

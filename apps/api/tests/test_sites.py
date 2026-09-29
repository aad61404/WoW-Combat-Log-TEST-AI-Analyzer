"""Retail vs classic Warcraft Logs sites: parsing, API routing, rules, and coach context."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.schemas import WCLSite
from app.routers.demo import demo_report, load
from app.routers.reports import _extract_report_code
from app.services.ai_coach import AICoach
from app.services.analyzer import CombatAnalyzer
from app.services.encounter_rules import get_rules_for_encounter
from app.services.wcl_client import WCLClient

CODE = "z7dxmQW2RBNC9br4"
ULGRAX = 2902


@pytest.mark.parametrize(
    ("url", "site"),
    [
        (f"https://www.warcraftlogs.com/reports/{CODE}", WCLSite.RETAIL),
        (f"https://warcraftlogs.com/reports/{CODE}", WCLSite.RETAIL),
        (f"https://tw.warcraftlogs.com/reports/{CODE}#fight=6", WCLSite.RETAIL),
        (f"https://classic.warcraftlogs.com/reports/{CODE}#fight=6", WCLSite.CLASSIC),
        (f"https://tw.classic.warcraftlogs.com/reports/{CODE}", WCLSite.CLASSIC),
        (f"https://sod.warcraftlogs.com/reports/{CODE}", WCLSite.SOD),
        (f"https://fresh.warcraftlogs.com/reports/{CODE}/", WCLSite.FRESH),
        (f"https://vanilla.warcraftlogs.com/reports/{CODE}", WCLSite.VANILLA),
    ],
)
def test_site_is_taken_from_url_host(url, site):
    assert _extract_report_code(url) == (CODE, site)


def test_url_host_overrides_site_parameter():
    url = f"https://classic.warcraftlogs.com/reports/{CODE}"
    assert _extract_report_code(url, WCLSite.RETAIL) == (CODE, WCLSite.CLASSIC)


def test_raw_code_uses_given_site_and_defaults_to_retail():
    assert _extract_report_code(CODE) == (CODE, WCLSite.RETAIL)
    assert _extract_report_code(CODE, WCLSite.VANILLA) == (CODE, WCLSite.VANILLA)


@pytest.mark.parametrize(
    "url",
    [
        f"https://classic.warcraftlogs.com.evil.example/reports/{CODE}",
        f"https://example.com/reports/{CODE}",
    ],
)
def test_non_wcl_hosts_are_rejected(url):
    with pytest.raises(HTTPException) as error:
        _extract_report_code(url)
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_classic_requests_use_classic_host_and_their_own_token(monkeypatch):
    monkeypatch.setattr(settings, "wcl_client_id", "local-test-client")
    monkeypatch.setattr(settings, "wcl_client_secret", "local-test-secret")
    report = load("sample_report.json")
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": f"token-{request.url.host}"})
        assert request.headers["authorization"] == f"Bearer token-{request.url.host}"
        return httpx.Response(200, json=report)

    client = WCLClient()
    await client._http.aclose()
    client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        classic = await client.get_report(CODE, WCLSite.CLASSIC)
        retail = await client.get_report(CODE)
    finally:
        await client.close()

    assert classic.site is WCLSite.CLASSIC
    assert retail.site is WCLSite.RETAIL
    assert requests == [
        WCLClient.token_url(WCLSite.CLASSIC),
        "https://classic.warcraftlogs.com/api/v2/client",
        WCLClient.token_url(WCLSite.RETAIL),
        "https://www.warcraftlogs.com/api/v2/client",
    ]


def test_routes_pass_site_through_to_wcl(monkeypatch):
    report = demo_report()
    report.code = CODE
    report.site = WCLSite.VANILLA
    raw = load("sample_events.json")
    get_report = AsyncMock(return_value=report)
    get_events = AsyncMock(
        return_value=(
            raw["data"]["reportData"]["report"]["events"]["data"],
            report.actors,
            raw["_abilityMap"],
        )
    )
    monkeypatch.setattr(WCLClient, "get_report", get_report)
    monkeypatch.setattr(WCLClient, "get_fight_events", get_events)
    monkeypatch.setattr(settings, "gemini_api_key", "")

    with TestClient(app) as client:
        summary = client.get(f"/api/reports/{CODE}", params={"site": "vanilla"})
        analysis = client.post(f"/api/reports/{CODE}/fights/1/analysis", params={"site": "vanilla"})
        invalid = client.get(f"/api/reports/{CODE}", params={"site": "tbc"})

    assert summary.status_code == 200
    assert summary.json()["site"] == "vanilla"
    assert analysis.status_code == 200
    assert all(call.args[-1] is WCLSite.VANILLA for call in get_report.await_args_list)
    assert get_events.await_args.args[-1] is WCLSite.VANILLA
    assert invalid.status_code == 422


def test_retail_rules_do_not_apply_to_classic_encounter_ids():
    assert get_rules_for_encounter(ULGRAX)
    assert get_rules_for_encounter(ULGRAX, WCLSite.CLASSIC) == []


def test_coach_message_carries_game_version():
    fight = demo_report().fights[0]
    analysis = CombatAnalyzer().analyze(fight, [], None)
    message = json.loads(AICoach()._build_user_message(fight, analysis, WCLSite.SOD))
    assert message["game_version"] == "sod"

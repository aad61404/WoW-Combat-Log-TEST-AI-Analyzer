"""HTTP-level contract regression: exercise the real client, no external requests."""

import json
from copy import deepcopy

import httpx
import pytest

from app.config import settings
from app.models.schemas import WCLSite
from app.routers.demo import load
from app.services.wcl_client import WCLClient, WCLAPIError


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setattr(settings, "wcl_client_id", "local-test-client")
    monkeypatch.setattr(settings, "wcl_client_secret", "local-test-secret")


async def client_with_transport(handler):
    client = WCLClient()
    await client._http.aclose()
    client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


@pytest.mark.asyncio
async def test_oauth_report_and_paginated_events_share_token(credentials):
    requests = []
    report = deepcopy(load("sample_report.json"))
    report["data"]["reportData"]["report"]["fights"][0].update(
        fightPercentage=70, bossPercentage=25
    )
    raw_events = load("sample_events.json")
    raw = raw_events["data"]["reportData"]["report"]["events"]["data"]
    actors = report["data"]["reportData"]["report"]["masterData"]["actors"]
    starts = []

    def handler(request):
        requests.append(request)
        if str(request.url) == WCLClient.token_url():
            assert request.headers["authorization"].startswith("Basic ")
            assert request.content == b"grant_type=client_credentials"
            return httpx.Response(200, json={"access_token": "local-token", "expires_in": 3600})
        assert str(request.url) == WCLClient.api_url()
        assert request.headers["authorization"] == "Bearer local-token"
        body = json.loads(request.content)
        assert body["variables"]["code"] == "AbCdEfGh12345678"
        if "query GetReport" in body["query"]:
            assert "bossPercentage" in body["query"]
            return httpx.Response(200, json=report)
        starts.append(body["variables"]["startTime"])
        first = len(starts) == 1
        return httpx.Response(
            200,
            json={
                "data": {
                    "reportData": {
                        "report": {
                            "events": {
                                "data": raw[:2] if first else raw[2:],
                                "nextPageTimestamp": 70000 if first else None,
                            },
                            "masterData": {
                                "actors": actors,
                                "abilities": [
                                    {"gameID": int(k), "name": v}
                                    for k, v in raw_events["_abilityMap"].items()
                                ],
                            },
                        }
                    }
                }
            },
        )

    client = await client_with_transport(handler)
    try:
        summary = await client.get_report("AbCdEfGh12345678")
        assert summary.fights[0].boss_percentage == 25
        assert summary.fights[0].fight_percentage == 70
        events, result_actors, abilities = await client.get_fight_events(
            summary.code, summary.fights[0]
        )
        assert events == raw
        assert starts == [60000, 70000]
        assert result_actors[0].name == actors[0]["name"]
        assert abilities[435136] == "Digestive Acid"
        assert sum(str(r.url) == WCLClient.token_url() for r in requests) == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_expired_token_is_refreshed(credentials):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"access_token": "fresh", "expires_in": 3600})

    client = await client_with_transport(handler)
    client._tokens[WCLSite.RETAIL] = ("expired", 0)
    try:
        assert await client._ensure_token() == "fresh"
        assert await client._ensure_token() == "fresh"
        assert len(calls) == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_graphql_errors_do_not_return_partial_analysis_or_raw_error(credentials):
    def handler(request):
        if str(request.url) == WCLClient.token_url():
            return httpx.Response(200, json={"access_token": "test"})
        return httpx.Response(
            200,
            json={
                "errors": [{"message": "private upstream details"}],
                "data": {"reportData": {"report": None}},
            },
        )

    client = await client_with_transport(handler)
    try:
        with pytest.raises(WCLAPIError) as error:
            await client.get_report("AbCdEfGh12345678")
        assert "private upstream" not in str(error.value)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_missing_boss_hp_is_not_replaced_by_encounter_progress(credentials):
    data = deepcopy(load("sample_report.json")["data"])
    report = data["reportData"]["report"]
    report["owner"] = None
    for fight in report["fights"]:
        fight.pop("bossPercentage")

    async def graphql(*args):
        return data

    client = WCLClient()
    client._graphql = graphql
    try:
        result = await client.get_report("AbCdEfGh12345678")
        assert result.owner == "Unknown"
        assert result.fights[0].boss_percentage is None
        assert result.fights[0].fight_percentage == 34.2
    finally:
        await client.close()

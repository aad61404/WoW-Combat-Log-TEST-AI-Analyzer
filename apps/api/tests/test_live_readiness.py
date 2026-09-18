"""Offline coverage for external-service failures and setup status."""

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.wcl_client import WCLClient, WCLAPIError

CODE = "AbCdEfGh12345678"


def test_status_reports_presence_without_secrets(monkeypatch):
    monkeypatch.setattr(settings, "wcl_client_id", "private-client-id")
    monkeypatch.setattr(settings, "wcl_client_secret", "private-client-secret")
    monkeypatch.setattr(settings, "gemini_api_key", "private-gemini-key")
    with TestClient(app) as client:
        response = client.get("/api/status")
    assert response.json() == {
        "wcl_configured": True,
        "gemini_configured": True,
        "demo_available": True,
    }
    assert "private" not in response.text


def test_missing_credentials_do_not_make_external_requests(monkeypatch):
    monkeypatch.setattr(settings, "wcl_client_id", "")
    monkeypatch.setattr(settings, "wcl_client_secret", "")
    with TestClient(app) as client:
        response = client.get(f"/api/reports/{CODE}")
    assert response.status_code == 503
    assert "WCL_CLIENT_ID" in response.json()["detail"]


@pytest.mark.parametrize(
    "upstream,expected", [(429, 429), (403, 403), (401, 403), (404, 404), (500, 502)]
)
def test_http_failures_have_safe_messages(monkeypatch, upstream, expected):
    request = httpx.Request("POST", "https://example.test/private")
    response = httpx.Response(upstream, request=request)
    error = httpx.HTTPStatusError("sensitive upstream details", request=request, response=response)
    monkeypatch.setattr(WCLClient, "get_report", AsyncMock(side_effect=error))
    with TestClient(app) as client:
        result = client.get(f"/api/reports/{CODE}")
    assert result.status_code == expected
    assert "sensitive" not in result.text
    assert "example.test" not in result.text


def test_timeout_has_retryable_message(monkeypatch):
    monkeypatch.setattr(
        WCLClient, "get_report", AsyncMock(side_effect=httpx.ReadTimeout("internal detail"))
    )
    with TestClient(app) as client:
        response = client.get(f"/api/reports/{CODE}")
    assert response.status_code == 504
    assert "逾時" in response.json()["detail"]


def test_invalid_report_code_rejected_before_fetch(monkeypatch):
    fetch = AsyncMock(side_effect=AssertionError("must not fetch"))
    monkeypatch.setattr(WCLClient, "get_report", fetch)
    with TestClient(app) as client:
        response = client.get("/api/reports/bad-code")
    assert response.status_code == 400
    fetch.assert_not_called()


@pytest.mark.asyncio
async def test_missing_report_is_not_an_internal_server_error():
    client = WCLClient()
    client._graphql = AsyncMock(return_value={"reportData": {"report": None}})
    try:
        with pytest.raises(WCLAPIError) as error:
            await client.get_report(CODE)
        assert error.value.status_code == 404
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_rejected_oauth_credentials_have_setup_message(monkeypatch):
    monkeypatch.setattr(settings, "wcl_client_id", "test-client")
    monkeypatch.setattr(settings, "wcl_client_secret", "test-secret")
    client = WCLClient()
    await client._http.aclose()
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(401))
    )
    try:
        with pytest.raises(WCLAPIError) as error:
            await client._ensure_token()
        assert error.value.status_code == 503
        assert "驗證失敗" in str(error.value)
    finally:
        await client.close()

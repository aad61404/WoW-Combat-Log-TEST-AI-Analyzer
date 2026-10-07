"""Persistence and import API regression tests; no external service is called."""

from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app
from app.models.database import Base
from app.repositories.reports import ReportRepository
from app.routers.demo import demo_report
from app.services.wcl_client import WCLClient


@pytest.fixture
async def database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield sessions
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_repository_round_trip_and_idempotent_refresh(database):
    report = demo_report()
    report.code = "AbCdEfGh12345678"
    async with database() as session:
        repository = ReportRepository(session)
        await repository.upsert(report)
        stored = await repository.get(report.code)
        assert stored == report

        refreshed = deepcopy(report)
        refreshed.title = "Updated title"
        refreshed.fights[0].boss_percentage = 12.5
        await repository.upsert(refreshed)
        stored = await repository.get(report.code)
        assert stored == refreshed
        assert len(stored.fights) == len(report.fights)
        assert len(stored.actors) == len(report.actors)


def test_import_endpoint_persists_and_get_uses_database(database, monkeypatch):
    report = demo_report()
    report.code = "AbCdEfGh12345678"
    fetch = AsyncMock(return_value=report)
    monkeypatch.setattr(WCLClient, "get_report", fetch)

    async def override_session():
        async with database() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/reports/import",
                json={"url": f"https://www.warcraftlogs.com/reports/{report.code}"},
            )
            assert response.status_code == 201
            assert response.json()["code"] == report.code

            fetch.reset_mock()
            stored = client.get(f"/api/reports/{report.code}")
            assert stored.status_code == 200
            assert stored.json()["title"] == report.title
            fetch.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()

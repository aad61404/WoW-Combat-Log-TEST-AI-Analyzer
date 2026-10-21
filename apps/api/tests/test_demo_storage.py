"""Detailed demo snapshots round-trip without WCL, AI, or fixture-file reads."""

from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app
from app.models.database import ActorRecord, Base, DemoSnapshotRecord, FightRecord, ReportRecord
from app.models.schemas import DemoSnapshot, FightCombatData
from app.repositories.reports import ReportRepository
from app.routers import demo
from app.services.ai_coach import AICoach
from app.services.wcl_client import WCLClient


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'snapshots.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.fixture
def snapshot():
    return DemoSnapshot(analysis=demo.demo_analysis(1), combat_data=demo.demo_combat_data(1))


@pytest.mark.asyncio
async def test_snapshot_roundtrip_update_and_counts(sessions, snapshot):
    async with sessions() as session:
        repository = ReportRepository(session)
        assert await repository.get_demo() is None
        await repository.save_demo(snapshot)
    # New connection and session prove this is persisted, not a Python cache.
    async with sessions() as session:
        repository = ReportRepository(session)
        stored = await repository.get_demo()
        assert stored.combat_data == snapshot.combat_data
        assert stored.analysis == snapshot.analysis
        assert stored.data_origin == "fixture"
        assert stored.database_engine == "sqlite"
        assert stored.storage == "database"
        assert stored.saved_at == snapshot.saved_at
        changed = deepcopy(snapshot)
        changed.combat_data.players[0].top_abilities[0].casts += 1
        await repository.save_demo(changed)
        assert (await repository.get_demo()).combat_data == changed.combat_data
        for model, expected in [
            (ReportRecord, 1),
            (FightRecord, 1),
            (ActorRecord, 21),
            (DemoSnapshotRecord, 1),
        ]:
            assert await session.scalar(select(func.count()).select_from(model)) == expected


@pytest.mark.asyncio
async def test_metadata_refresh_invalidates_snapshot(sessions, snapshot):
    async with sessions() as session:
        repository = ReportRepository(session)
        await repository.save_demo(snapshot)
        await repository.upsert(snapshot.analysis.report)
        assert await repository.get_demo() is None


@pytest.mark.asyncio
async def test_failed_refresh_rolls_back_complete_previous_snapshot(
    sessions, snapshot, monkeypatch
):
    async with sessions() as session:
        repository = ReportRepository(session)
        await repository.save_demo(snapshot)
        changed = deepcopy(snapshot)
        changed.analysis.report.title = "Must not survive failed commit"

        # Flush to exercise actual deletes/inserts, then fail the commit.
        async def fail_commit():
            await session.flush()
            raise OperationalError("commit", {}, RuntimeError("unavailable"))

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(OperationalError):
            await repository.save_demo(changed)
    async with sessions() as session:
        repository = ReportRepository(session)
        assert (await repository.get_demo()).analysis == snapshot.analysis
        assert await repository.get("demo") == snapshot.analysis.report


@pytest.mark.parametrize(
    "field,value",
    [
        ("player_count", 19),
        ("duration_seconds", 0),
    ],
)
def test_combat_invalid_totals_rejected(snapshot, field, value):
    raw = snapshot.combat_data.model_dump()
    raw[field] = value
    with pytest.raises(ValidationError):
        FightCombatData.model_validate(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("deaths", -1),
        ("dps", -1),
        ("hps", float("inf")),
        ("active_time_percentage", 101),
        ("total_damage", -1),
    ],
)
def test_combat_invalid_player_values_rejected(snapshot, field, value):
    raw = snapshot.combat_data.model_dump()
    raw["players"][0][field] = value
    with pytest.raises(ValidationError):
        FightCombatData.model_validate(raw)


def test_combat_duplicate_players_and_invalid_critical_hits(snapshot):
    raw = snapshot.combat_data.model_dump()
    raw["players"][1]["actor_id"] = raw["players"][0]["actor_id"]
    with pytest.raises(ValidationError):
        FightCombatData.model_validate(raw)
    raw = snapshot.combat_data.model_dump()
    raw["players"][0]["top_abilities"][0]["critical_hits"] = 9999
    with pytest.raises(ValidationError):
        FightCombatData.model_validate(raw)


@pytest.mark.parametrize(
    "path,value",
    [
        (("analysis", "demo"), False),
        (("analysis", "report", "code"), "AbCdEfGh12345678"),
        (("combat_data", "fight_id"), 2),
        (("combat_data", "duration_seconds"), 999),
        (("combat_data", "players", 0, "name"), "Wrong player"),
        (("combat_data", "players", 0, "actor_id"), 100),
        (("combat_data", "players", 0, "deaths"), 1),
        (("analysis", "analysis", "total_deaths"), 5),
    ],
)
def test_snapshot_cross_file_consistency(snapshot, path, value):
    raw = snapshot.model_dump()
    node = raw
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value
    with pytest.raises(ValidationError):
        DemoSnapshot.model_validate(raw)


@pytest.mark.asyncio
async def test_invalid_snapshot_never_changes_database(sessions, snapshot):
    async with sessions() as session:
        repository = ReportRepository(session)
        await repository.save_demo(snapshot)
        invalid = deepcopy(snapshot)
        invalid.combat_data.players[0].deaths = 99
        with pytest.raises(ValidationError):
            await repository.save_demo(invalid)
        assert (await repository.get_demo()).combat_data == snapshot.combat_data


def test_snapshot_api_is_offline_and_reads_only_database(sessions, monkeypatch):
    external = AsyncMock(side_effect=AssertionError("External API must not be called"))
    monkeypatch.setattr(WCLClient, "_graphql", external)
    monkeypatch.setattr(AICoach, "generate_report", external)

    async def override_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            assert client.get("/api/demo/stored").status_code == 404
            created = client.post("/api/demo/import")
            assert created.status_code == 200
            assert created.json()["combat_data"]["player_count"] == 20
            again = client.post("/api/demo/import")
            assert again.status_code == 200

            def no_fixture_reads(*args):
                raise AssertionError("Stored results must not be loaded from fixtures")

            monkeypatch.setattr(demo, "load", no_fixture_reads)
            fetched = client.get("/api/demo/stored")
            assert fetched.status_code == 200
            assert fetched.json() == again.json()
            external.assert_not_awaited()
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.parametrize("method,path", [("get", "/api/demo/stored"), ("post", "/api/demo/import")])
@pytest.mark.parametrize(
    "failure",
    [
        OperationalError("SELECT", {}, RuntimeError("secret-connection-string")),
        ConnectionRefusedError("secret-connection-string"),
    ],
)
def test_database_failure_returns_safe_retryable_error(method, path, failure, monkeypatch):
    failing = AsyncMock(side_effect=failure)
    monkeypatch.setattr(ReportRepository, "get_demo", failing)
    monkeypatch.setattr(ReportRepository, "save_demo", failing)
    with TestClient(app) as client:
        response = getattr(client, method)(path)
        assert response.status_code == 503
        assert "資料庫連線" in response.json()["detail"]
        assert "secret-connection-string" not in response.text

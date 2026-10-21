"""Explicit local fixture demo. Never calls WCL or Gemini."""

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.schemas import (
    Actor,
    DemoSnapshot,
    FightCombatData,
    FightSummary,
    FullAnalysisResponse,
    ReportSummary,
    StoredDemoSnapshot,
)
from app.repositories.reports import ReportRepository
from app.services.ai_coach import AICoach
from app.services.analyzer import CombatAnalyzer
from app.services.encounter_rules import get_rules_for_encounter
from app.services.normalizer import normalize_events

router = APIRouter(prefix="/api/demo", tags=["demo"])
FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures"
logger = logging.getLogger(__name__)
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@router.get("/report")
def demo_report() -> ReportSummary:
    raw = load("sample_report.json")["data"]["reportData"]["report"]
    # Only fight 1 has event data. Do not invent analyses for other fights.
    f = raw["fights"][0]
    return ReportSummary(
        code="demo",
        title="Nerub-ar Palace · 範例戰報",
        owner=raw["owner"]["name"],
        start_time=raw["startTime"],
        end_time=raw["endTime"],
        fights=[
            FightSummary(
                id=f["id"],
                name=f["name"],
                start_time=f["startTime"],
                end_time=f["endTime"],
                kill=f["kill"],
                difficulty=f["difficulty"],
                encounter_id=f["encounterID"],
                fight_percentage=f["fightPercentage"],
                boss_percentage=f.get("bossPercentage"),
            )
        ],
        actors=[
            Actor(
                id=a["id"],
                name=a["name"],
                type=a["type"],
                sub_type=a.get("subType", ""),
                server=a.get("server"),
            )
            for a in raw["masterData"]["actors"]
        ],
    )


@router.get("/fights/{fight_id}/combat-data")
def demo_combat_data(fight_id: int) -> FightCombatData:
    report = demo_report()
    fight = next((item for item in report.fights if item.id == fight_id), None)
    if fight is None:
        raise HTTPException(404, "這場戰鬥沒有範例資料。")
    raw = load("sample_combat_data.json")
    if raw["fight_id"] != fight_id:
        raise HTTPException(404, "這場戰鬥沒有詳細範例資料。")
    return FightCombatData.model_validate(raw)


@router.post("/fights/{fight_id}/analysis")
def demo_analysis(fight_id: int) -> FullAnalysisResponse:
    report = demo_report()
    if fight_id != report.fights[0].id:
        raise HTTPException(404, "這場戰鬥沒有範例事件資料。")
    fight = report.fights[0]
    raw = load("sample_events.json")
    events = normalize_events(
        raw["data"]["reportData"]["report"]["events"]["data"],
        report.actors,
        fight.start_time,
        raw.get("_abilityMap", {}),
    )
    analysis = CombatAnalyzer().analyze(fight, events, get_rules_for_encounter(fight.encounter_id))
    return FullAnalysisResponse(
        demo=True,
        rule_notice="範例資料與示範規則，僅供體驗；不代表真實 Boss 機制判定。",
        report=report,
        fight=fight,
        analysis=analysis,
        coach_report=AICoach._build_fallback_report(fight, analysis),
    )


@router.post("/import", response_model=StoredDemoSnapshot)
async def import_demo(session: DatabaseSession) -> StoredDemoSnapshot:
    """Create or replace the local demo snapshot atomically. No external APIs."""
    snapshot = DemoSnapshot(analysis=demo_analysis(1), combat_data=demo_combat_data(1))
    repository = ReportRepository(session)
    try:
        await repository.save_demo(snapshot)
        stored = await repository.get_demo()
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Demo persistence failed (%s)", type(exc).__name__)
        raise HTTPException(503, "無法儲存範例，請確認資料庫連線後重試。") from exc
    if stored is None:
        raise HTTPException(503, "範例尚未成功讀回，請重試。")
    return stored


@router.get("/stored", response_model=StoredDemoSnapshot)
async def stored_demo(session: DatabaseSession) -> StoredDemoSnapshot:
    """Read only from DB; never reload fixtures or silently call WCL/AI."""
    try:
        snapshot = await ReportRepository(session).get_demo()
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Demo query failed (%s)", type(exc).__name__)
        raise HTTPException(503, "無法讀取範例，請確認資料庫連線後重試。") from exc
    if snapshot is None:
        raise HTTPException(404, "資料庫尚無完整範例，請先按「儲存範例到 DB」。")
    return snapshot

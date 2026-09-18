"""Explicit local fixture demo. Never calls WCL or Gemini."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.models.schemas import Actor, FightSummary, ReportSummary, FullAnalysisResponse
from app.services.normalizer import normalize_events
from app.services.analyzer import CombatAnalyzer
from app.services.encounter_rules import get_rules_for_encounter
from app.services.ai_coach import AICoach

router = APIRouter(prefix="/api/demo", tags=["demo"])
FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures"


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

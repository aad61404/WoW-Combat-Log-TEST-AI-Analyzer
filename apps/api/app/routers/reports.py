"""
Reports router — REST API endpoints for WCL report analysis.

Two endpoints:
  GET  /api/reports/{code}                          — Fetch report summary
  POST /api/reports/{code}/fights/{fight_id}/analysis — Full analysis pipeline
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisResult, FullAnalysisResponse, ReportSummary
from app.services.ai_coach import AICoach
from app.services.analyzer import CombatAnalyzer
from app.services.encounter_rules import get_rules_for_encounter
from app.services.normalizer import normalize_events

router = APIRouter(prefix="/api", tags=["reports"])
logger = logging.getLogger(__name__)

# Regex to extract report code from a WCL URL
WCL_URL_PATTERN = re.compile(r"warcraftlogs\.com/reports/([a-zA-Z0-9]+)")


def _get_wcl_client():
    """Get the global WCL client from the app state."""
    from app.main import wcl_client

    if wcl_client is None:
        raise HTTPException(status_code=503, detail="WCL client not initialized")
    return wcl_client


def _extract_report_code(code_or_url: str) -> str:
    """
    Extract report code from either a raw code or a full WCL URL.

    Supports:
      - "AbCdEf1234" (raw code)
      - "https://www.warcraftlogs.com/reports/AbCdEf1234"
      - "https://www.warcraftlogs.com/reports/AbCdEf1234#fight=5"
    """
    match = WCL_URL_PATTERN.search(code_or_url)
    if match:
        return match.group(1)
    # Assume it's already a raw code
    return code_or_url.strip()


@router.get("/reports/{code}")
async def get_report(code: str) -> ReportSummary:
    """
    Fetch report summary from Warcraft Logs.

    Returns fight list and player roster.
    This is a lightweight call — no analysis performed.
    """
    client = _get_wcl_client()
    report_code = _extract_report_code(code)

    try:
        return await client.get_report(report_code)
    except Exception as e:
        logger.error(f"Failed to fetch report {report_code}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch report from Warcraft Logs: {str(e)}",
        )


@router.post("/reports/{code}/fights/{fight_id}/analysis")
async def analyze_fight(code: str, fight_id: int) -> FullAnalysisResponse:
    """
    Complete analysis pipeline for a specific fight.

    Pipeline:
    1. Fetch report summary from WCL
    2. Fetch fight events from WCL (with pagination)
    3. Normalize events
    4. Run encounter-specific rules
    5. Deterministic analysis (deaths + evidence)
    6. AI coach report generation (Gemini)
    7. Return combined result

    This is a POST because it:
    - Costs API tokens (WCL + Gemini)
    - May not be deterministic (LLM output)
    - Should not be cached/prefetched by browsers
    """
    client = _get_wcl_client()
    report_code = _extract_report_code(code)

    # 1. Fetch report summary
    try:
        report = await client.get_report(report_code)
    except Exception as e:
        logger.error(f"Failed to fetch report {report_code}: {e}")
        raise HTTPException(status_code=502, detail=f"WCL report fetch failed: {e}")

    # 2. Find the specified fight
    fight = next((f for f in report.fights if f.id == fight_id), None)
    if fight is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fight {fight_id} not found in report {report_code}",
        )

    # 3. Fetch fight events
    try:
        raw_events, actors = await client.get_fight_events(report_code, fight)
    except Exception as e:
        logger.error(f"Failed to fetch events for fight {fight_id}: {e}")
        raise HTTPException(status_code=502, detail=f"WCL events fetch failed: {e}")

    # 4. Normalize events
    normalized = normalize_events(
        raw_events=raw_events,
        actors=actors,
        fight_start_time=fight.start_time,
    )

    # 5. Run encounter rules + deterministic analysis
    rules = get_rules_for_encounter(fight.encounter_id)
    analyzer = CombatAnalyzer()
    analysis: AnalysisResult = analyzer.analyze(fight, normalized, rules)

    # 6. AI coach report
    try:
        coach = AICoach()
        coach_report = await coach.generate_report(fight, analysis)
    except Exception as e:
        logger.error(f"AI coach failed: {e}")
        # Use fallback report
        coach = AICoach()
        coach_report = coach._build_fallback_report(fight, analysis)

    # 7. Return combined result
    return FullAnalysisResponse(
        report=report,
        fight=fight,
        analysis=analysis,
        coach_report=coach_report,
    )

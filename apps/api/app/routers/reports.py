"""
Reports router — REST API endpoints for WCL report analysis.

Two endpoints:
  GET  /api/reports/{code}                          — Fetch report summary
  POST /api/reports/{code}/fights/{fight_id}/analysis — Full analysis pipeline
"""

from __future__ import annotations

import logging
import re
import httpx
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisResult, FullAnalysisResponse, ReportSummary
from app.services.ai_coach import AICoach
from app.services.analyzer import CombatAnalyzer
from app.services.normalizer import normalize_events
from app.services.wcl_client import WCLAPIError

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
    text = code_or_url.strip()
    if re.fullmatch(r"[a-zA-Z0-9]{16}", text):
        return text
    url = urlparse(text)
    host = url.hostname or ""
    if url.scheme in ("http", "https") and (
        host == "warcraftlogs.com" or host.endswith(".warcraftlogs.com")
    ):
        match = re.fullmatch(r"/reports/([a-zA-Z0-9]{16})/?", url.path)
        if match:
            return match.group(1)
    raise HTTPException(400, "請提供有效的 Warcraft Logs 網址或 16 碼報告代碼。")


def _upstream_error(error: Exception) -> HTTPException:
    if isinstance(error, WCLAPIError):
        return HTTPException(error.status_code, str(error))
    if isinstance(error, httpx.TimeoutException):
        return HTTPException(504, "WCL 回應逾時，請稍後重試。")
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status == 429:
            return HTTPException(429, "WCL 請求額度已達上限，請稍後再試。")
        if status in (401, 403):
            return HTTPException(403, "WCL 拒絕存取，請確認憑證與戰報公開權限。")
        if status == 404:
            return HTTPException(404, "找不到此 WCL 戰報。")
    return HTTPException(502, "暫時無法讀取 WCL 資料，請稍後重試。")


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
        logger.warning("Report request failed: %s", type(e).__name__)
        raise _upstream_error(e) from e


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
        logger.warning("Report request failed: %s", type(e).__name__)
        raise _upstream_error(e) from e

    # 2. Find the specified fight
    fight = next((f for f in report.fights if f.id == fight_id), None)
    if fight is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fight {fight_id} not found in report {report_code}",
        )

    # 3. Fetch fight events
    try:
        raw_events, actors, ability_names = await client.get_fight_events(report_code, fight)
    except Exception as e:
        logger.warning("Event request failed: %s", type(e).__name__)
        raise _upstream_error(e) from e

    # 4. Normalize events
    normalized = normalize_events(
        raw_events=raw_events,
        actors=actors,
        fight_start_time=fight.start_time,
        ability_map=ability_names,
    )

    # 5. Run encounter rules + deterministic analysis
    # Registry entries are fixture examples, not validated live boss mechanics.
    rules = []
    analyzer = CombatAnalyzer()
    analysis: AnalysisResult = analyzer.analyze(fight, normalized, rules)

    # 6. AI coach report
    try:
        coach = AICoach()
        coach_report = await coach.generate_report(fight, analysis)
    except Exception as e:
        logger.error(f"AI coach failed: {e}")
        # Use fallback report
        coach_report = AICoach._build_fallback_report(fight, analysis)

    # 7. Return combined result
    return FullAnalysisResponse(
        report=report,
        fight=fight,
        analysis=analysis,
        coach_report=coach_report,
    )

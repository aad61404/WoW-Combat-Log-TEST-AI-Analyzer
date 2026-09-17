"""
Pydantic models — the API contract for the entire system.

All modules (WCL client, normalizer, analyzer, AI coach, REST API, frontend)
share these models as their common language.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# WCL Data Models
# =============================================================================


class Actor(BaseModel):
    """A participant in the combat log (player, NPC, or pet)."""

    id: int
    name: str
    type: str  # "Player", "NPC", "Pet"
    sub_type: str = ""  # "Paladin", "Warrior", etc.
    server: str | None = None


class FightSummary(BaseModel):
    """Summary of a single fight (boss encounter or trash pull)."""

    id: int
    name: str  # Boss name
    start_time: int  # ms, relative to report start
    end_time: int  # ms, relative to report start
    kill: bool
    difficulty: int | None = None
    encounter_id: int
    fight_percentage: float | None = None  # Boss HP % at wipe (0 = dead)

    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time) / 1000.0

    @property
    def duration_display(self) -> str:
        total = int(self.duration_seconds)
        minutes, seconds = divmod(total, 60)
        return f"{minutes}:{seconds:02d}"


class ReportSummary(BaseModel):
    """Summary of a full Warcraft Logs report."""

    code: str
    title: str
    owner: str
    start_time: int  # epoch ms
    end_time: int  # epoch ms
    fights: list[FightSummary]
    actors: list[Actor]


# =============================================================================
# Normalized Events
# =============================================================================


class NormalizedEvent(BaseModel):
    """
    A combat log event normalized from WCL raw format.

    All timestamps are relative to fight start (ms).
    Source/target names are resolved from actor IDs.
    """

    timestamp: int  # ms, relative to fight start
    type: str  # death, damage, heal, debuff_apply, debuff_remove, cast, interrupt, begin_cast
    source_id: int | None = None
    source_name: str | None = None
    target_id: int | None = None
    target_name: str | None = None
    ability_id: int | None = None
    ability_name: str | None = None
    amount: int | None = None
    extra: dict | None = Field(default_factory=dict)
    # extra may contain: overkill, overheal, absorbed, stacks, hitType, etc.


# =============================================================================
# Analysis Evidence
# =============================================================================


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class EvidenceType(str, Enum):
    DEATH = "death"
    MECHANIC_FAIL = "mechanic_fail"
    MISSED_INTERRUPT = "missed_interrupt"
    DEBUFF_STACK_EXCEEDED = "debuff_stack_exceeded"


class Evidence(BaseModel):
    """
    A single piece of deterministic evidence from the analyzer.

    This is NOT a guess — it is confirmed by Python rule evaluation.
    The description is factual, not speculative.
    """

    timestamp: int  # ms, relative to fight start
    type: EvidenceType
    severity: Severity
    player: str | None = None  # None for raid-wide events
    description: str  # Factual description, not AI-generated
    details: dict = Field(default_factory=dict)
    # details may contain: ability_id, ability_name, damage_amount, stack_count, etc.

    @property
    def timestamp_display(self) -> str:
        total_seconds = self.timestamp // 1000
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


class DamageEntry(BaseModel):
    """A single damage event in the death timeline."""

    source: str
    ability: str
    amount: int
    timestamp: int  # ms, relative to fight start


class DeathDetail(BaseModel):
    """Detailed information about a player death."""

    player: str
    timestamp: int  # ms, relative to fight start
    killing_blow: str | None = None  # ability name
    damage_taken_last_5s: list[DamageEntry] = Field(default_factory=list)

    @property
    def timestamp_display(self) -> str:
        total_seconds = self.timestamp // 1000
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


class AnalysisResult(BaseModel):
    """Complete deterministic analysis result for a fight."""

    fight: FightSummary
    deaths: list[DeathDetail]
    evidence: list[Evidence]
    total_deaths: int
    fight_duration_seconds: float


# =============================================================================
# AI Coach Report
# =============================================================================


class PlayerAdvice(BaseModel):
    """AI-generated advice for a specific player."""

    player: str
    issues: list[str]
    suggestions: list[str]


class CoachReport(BaseModel):
    """AI-generated coaching report based on deterministic evidence."""

    wipe_summary: str  # 1-2 sentence summary
    primary_causes: list[str]  # Top 3-5 wipe causes
    player_advice: list[PlayerAdvice]  # Per-player advice
    priority_fixes: list[str]  # What to fix first next pull


# =============================================================================
# API Response
# =============================================================================


class FullAnalysisResponse(BaseModel):
    """
    Combined response from POST /api/reports/{code}/fights/{fightId}/analysis.

    Contains everything the frontend needs in a single response:
    report context, fight details, deterministic analysis, and AI coaching.
    """

    report: ReportSummary
    fight: FightSummary
    analysis: AnalysisResult
    coach_report: CoachReport

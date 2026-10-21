"""
Pydantic models — the API contract for the entire system.

All modules (WCL client, normalizer, analyzer, AI coach, REST API, frontend)
share these models as their common language.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# =============================================================================
# WCL Data Models
# =============================================================================


class WCLSite(str, Enum):
    """Warcraft Logs site; each has its own report database and API host."""

    RETAIL = "retail"
    CLASSIC = "classic"
    FRESH = "fresh"
    SOD = "sod"
    VANILLA = "vanilla"

    @property
    def host(self) -> str:
        return (
            "www.warcraftlogs.com" if self is WCLSite.RETAIL else f"{self.value}.warcraftlogs.com"
        )


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
    fight_percentage: float | None = None  # Encounter progress, not necessarily boss HP
    boss_percentage: float | None = None  # Remaining HP of active boss(es)

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
    site: WCLSite = WCLSite.RETAIL
    title: str
    owner: str
    start_time: int  # epoch ms
    end_time: int  # epoch ms
    fights: list[FightSummary]
    actors: list[Actor]


class ReportImportRequest(BaseModel):
    """A WCL report URL or 16-character report code to import."""

    url: str


class AbilityUsage(BaseModel):
    """Aggregated ability numbers for the offline demo dataset."""

    ability_id: int
    ability_name: str
    casts: int = Field(ge=0)
    hits: int = Field(ge=0)
    total: int = Field(ge=0)
    critical_hits: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_hits(self) -> AbilityUsage:
        if self.critical_hits > self.hits:
            raise ValueError("critical_hits cannot exceed hits")
        return self


class PlayerCombatSummary(BaseModel):
    """Per-player combat summary shaped like data derived from WCL tables."""

    actor_id: int
    name: str
    class_name: str
    spec: str
    role: Literal["tank", "healer", "dps"]
    item_level: int = Field(ge=0)
    total_damage: int = Field(ge=0)
    dps: float = Field(ge=0, allow_inf_nan=False)
    total_healing: int = Field(ge=0)
    hps: float = Field(ge=0, allow_inf_nan=False)
    deaths: int = Field(ge=0)
    interrupts: int = Field(ge=0)
    active_time_percentage: float = Field(ge=0, le=100, allow_inf_nan=False)
    top_abilities: list[AbilityUsage]


class FightCombatData(BaseModel):
    """Detailed demo data. It must never be presented as a live WCL response."""

    data_origin: Literal["fixture"] = "fixture"
    notice: str
    fight_id: int
    duration_seconds: float = Field(gt=0, allow_inf_nan=False)
    player_count: int = Field(ge=0)
    players: list[PlayerCombatSummary]

    @model_validator(mode="after")
    def check_roster(self) -> FightCombatData:
        ids = [player.actor_id for player in self.players]
        if self.player_count != len(ids) or len(set(ids)) != len(ids):
            raise ValueError("player_count must match a unique player roster")
        return self


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
    player_id: int | None = None
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
    player_id: int | None = None
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

    source: Literal["ai", "deterministic"] = "ai"
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

    demo: bool = False
    rule_notice: str = "目前僅分析死亡紀錄；Boss 機制規則尚待真實資料驗證。"
    report: ReportSummary
    fight: FightSummary
    analysis: AnalysisResult
    coach_report: CoachReport


class DemoSnapshot(BaseModel):
    """One consistent, explicitly synthetic analysis and combat-data snapshot."""

    schema_version: Literal[1] = 1
    data_origin: Literal["fixture"] = "fixture"
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    analysis: FullAnalysisResponse
    combat_data: FightCombatData

    @model_validator(mode="after")
    def check_consistency(self) -> DemoSnapshot:
        result = self.analysis
        combat = self.combat_data
        report = result.report
        if not result.demo or report.code != "demo":
            raise ValueError("Only the explicitly marked demo report can be saved here")
        if result.fight not in report.fights or result.analysis.fight != result.fight:
            raise ValueError("Analysis fight must belong to the snapshot report")
        if combat.fight_id != result.fight.id:
            raise ValueError("Combat data must belong to the analyzed fight")
        if combat.duration_seconds != result.fight.duration_seconds:
            raise ValueError("Combat duration must match the fight")
        roster = {actor.id: actor for actor in report.actors if actor.type == "Player"}
        if set(roster) != {player.actor_id for player in combat.players}:
            raise ValueError("Combat players must match the report player roster")
        deaths = Counter(death.player_id for death in result.analysis.deaths)
        if result.analysis.total_deaths != len(result.analysis.deaths):
            raise ValueError("Analysis death count must match death events")
        if set(deaths) - set(roster):
            raise ValueError("Death events must reference known players")
        for player in combat.players:
            if player.name != roster[player.actor_id].name:
                raise ValueError("Combat player names must match the report roster")
            if player.deaths != deaths[player.actor_id]:
                raise ValueError("Combat deaths must match the analyzed death events")
        return self


class StoredDemoSnapshot(DemoSnapshot):
    storage: Literal["database"] = "database"
    database_engine: Literal["postgresql", "sqlite"]

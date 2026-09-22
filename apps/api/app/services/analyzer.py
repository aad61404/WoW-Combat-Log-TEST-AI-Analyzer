"""
Deterministic Combat Analyzer.

Takes normalized events + encounter rules and produces:
1. Death timeline with damage-before-death details
2. Rule-based evidence (mechanic fails, missed interrupts, debuff stacks)

The analyzer does NOT guess or use AI — every piece of evidence
is confirmed by explicit rule evaluation.
"""

from __future__ import annotations

from collections import defaultdict, deque

from app.models.schemas import (
    AnalysisResult,
    DamageEntry,
    DeathDetail,
    Evidence,
    EvidenceType,
    FightSummary,
    NormalizedEvent,
    Severity,
)
from app.services.encounter_rules.base import EncounterRule

# How many milliseconds before death to look for damage events
DAMAGE_WINDOW_MS = 5000


class CombatAnalyzer:
    """Deterministic combat log analyzer."""

    def analyze(
        self,
        fight: FightSummary,
        events: list[NormalizedEvent],
        encounter_rules: list[EncounterRule] | None = None,
    ) -> AnalysisResult:
        """
        Perform deterministic analysis of a fight.

        Args:
            fight: Fight metadata (boss name, duration, kill/wipe).
            events: Normalized events from the normalizer.
            encounter_rules: Boss-specific rules to evaluate.
                If None, only death timeline analysis is performed.

        Returns:
            AnalysisResult with deaths, evidence, and summary stats.
        """
        # Bound analysis to this fight; preserve the order of equal timestamps.
        events = sorted(
            (e for e in events if 0 <= e.timestamp <= fight.end_time - fight.start_time),
            key=lambda e: e.timestamp,
        )

        # 1. Build death timeline
        deaths = self._analyze_deaths(events)

        # 2. Collect evidence from encounter rules
        evidence: list[Evidence] = []

        # Add death events as evidence
        for death in deaths:
            evidence.append(
                Evidence(
                    timestamp=death.timestamp,
                    type=EvidenceType.DEATH,
                    severity=Severity.CRITICAL,
                    player=death.player,
                    player_id=death.player_id,
                    description=(
                        f"{death.player} 死亡"
                        + (f"（致命一擊：{death.killing_blow}）" if death.killing_blow else "")
                    ),
                    details={
                        "killing_blow": death.killing_blow,
                        "damage_taken_last_5s_total": sum(
                            d.amount for d in death.damage_taken_last_5s
                        ),
                    },
                )
            )

        # 3. Run encounter-specific rules
        if encounter_rules:
            for rule in encounter_rules:
                rule_evidence = rule.evaluate(events)
                evidence.extend(rule_evidence)

        # 4. Sort all evidence by timestamp
        evidence.sort(key=lambda e: e.timestamp)

        return AnalysisResult(
            fight=fight,
            deaths=deaths,
            evidence=evidence,
            total_deaths=len(deaths),
            fight_duration_seconds=fight.duration_seconds,
        )

    def _analyze_deaths(self, events: list[NormalizedEvent]) -> list[DeathDetail]:
        """
        Build detailed death timeline.

        For each death, collects all damage events within
        DAMAGE_WINDOW_MS before the death timestamp.
        """
        recent: dict[tuple[str, int | str], deque[NormalizedEvent]] = defaultdict(deque)
        deaths: list[DeathDetail] = []
        for event in events:
            if event.type not in ("damage", "death") or not event.target_name:
                continue
            # Actor IDs distinguish same-name players from different realms.
            key = (
                ("id", event.target_id)
                if event.target_id is not None
                else ("name", event.target_name)
            )
            window = recent[key]
            while window and window[0].timestamp < event.timestamp - DAMAGE_WINDOW_MS:
                window.popleft()
            if event.type == "damage":
                window.append(event)
                continue
            deaths.append(
                DeathDetail(
                    player=event.target_name,
                    player_id=event.target_id,
                    timestamp=event.timestamp,
                    killing_blow=event.ability_name,
                    damage_taken_last_5s=[
                        DamageEntry(
                            source=d.source_name or "Unknown",
                            ability=d.ability_name
                            or (
                                f"Ability #{d.ability_id}"
                                if d.ability_id is not None
                                else "Unknown"
                            ),
                            amount=d.amount or 0,
                            timestamp=d.timestamp,
                        )
                        for d in window
                    ],
                )
            )
            # A second death after resurrection must not reuse the previous life.
            window.clear()
        return deaths

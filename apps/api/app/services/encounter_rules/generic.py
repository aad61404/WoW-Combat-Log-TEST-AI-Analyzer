"""
Generic Encounter Rules — reusable across multiple bosses.

Each rule is parameterized by ability IDs and thresholds.
Boss definitions compose these rules with specific IDs.
"""

from __future__ import annotations

from app.models.schemas import Evidence, EvidenceType, NormalizedEvent, Severity

from .base import EncounterRule


class AvoidableDamageRule(EncounterRule):
    """
    Detects players hit by avoidable damage abilities.

    If a player takes damage from a known avoidable ability,
    this is a confirmed mechanic failure — not a guess.
    """

    def __init__(
        self,
        ability_id: int,
        ability_name: str,
        threshold: int = 0,
        severity: Severity = Severity.CRITICAL,
    ) -> None:
        self.ability_id = ability_id
        self.ability_name = ability_name
        self.threshold = threshold
        self.severity = severity
        self.name = f"AvoidableDamage({ability_name})"
        self.description = f"Detects players hit by avoidable ability: {ability_name}"

    def evaluate(self, events: list[NormalizedEvent]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for event in events:
            if (
                event.type == "damage"
                and event.ability_id == self.ability_id
                and event.target_name is not None
                and (event.amount or 0) > self.threshold
            ):
                evidence.append(
                    Evidence(
                        timestamp=event.timestamp,
                        type=EvidenceType.MECHANIC_FAIL,
                        severity=self.severity,
                        player=event.target_name,
                        description=(
                            f"被可迴避技能 {self.ability_name} 命中，"
                            f"受到 {event.amount:,} 傷害"
                        ),
                        details={
                            "ability_id": self.ability_id,
                            "ability_name": self.ability_name,
                            "damage_amount": event.amount,
                            "rule": self.name,
                        },
                    )
                )
        return evidence


class InterruptRule(EncounterRule):
    """
    Detects casts that should have been interrupted but weren't.

    Logic: if we see a begincast for the target ability followed by
    a cast (completion) without an interrupt event in between,
    that's a missed interrupt.
    """

    def __init__(
        self,
        ability_id: int,
        ability_name: str,
        severity: Severity = Severity.WARNING,
    ) -> None:
        self.ability_id = ability_id
        self.ability_name = ability_name
        self.severity = severity
        self.name = f"Interrupt({ability_name})"
        self.description = f"Detects missed interrupts on: {ability_name}"

    def evaluate(self, events: list[NormalizedEvent]) -> list[Evidence]:
        evidence: list[Evidence] = []

        # Track begincast → look for interrupt or cast completion
        pending_casts: list[NormalizedEvent] = []

        for event in events:
            if event.type == "begin_cast" and event.ability_id == self.ability_id:
                pending_casts.append(event)

            elif event.type == "interrupt" and pending_casts:
                # Check if this interrupt stopped our tracked ability
                interrupted_ability = (event.extra or {}).get("extraAbilityGameID")
                if interrupted_ability == self.ability_id:
                    # Successfully interrupted — remove from pending
                    if pending_casts:
                        pending_casts.pop()

            elif event.type == "cast" and event.ability_id == self.ability_id:
                # Cast completed — this means no interrupt happened
                if pending_casts:
                    begin_event = pending_casts.pop(0)
                    evidence.append(
                        Evidence(
                            timestamp=event.timestamp,
                            type=EvidenceType.MISSED_INTERRUPT,
                            severity=self.severity,
                            player=None,  # Raid-wide responsibility
                            description=(
                                f"{self.ability_name} 施法未被打斷"
                            ),
                            details={
                                "ability_id": self.ability_id,
                                "ability_name": self.ability_name,
                                "cast_start": begin_event.timestamp,
                                "cast_end": event.timestamp,
                                "caster": event.source_name,
                                "rule": self.name,
                            },
                        )
                    )

        return evidence


class DebuffStackRule(EncounterRule):
    """
    Detects players who accumulated too many stacks of a debuff.

    This is deterministic: if the WCL log shows stack count > max_safe_stacks,
    it means the player failed to drop stacks in time.
    """

    def __init__(
        self,
        ability_id: int,
        ability_name: str,
        max_safe_stacks: int,
        severity: Severity = Severity.WARNING,
    ) -> None:
        self.ability_id = ability_id
        self.ability_name = ability_name
        self.max_safe_stacks = max_safe_stacks
        self.severity = severity
        self.name = f"DebuffStack({ability_name}, max={max_safe_stacks})"
        self.description = (
            f"Detects players exceeding {max_safe_stacks} stacks of {ability_name}"
        )

    def evaluate(self, events: list[NormalizedEvent]) -> list[Evidence]:
        evidence: list[Evidence] = []
        # Track which players we've already flagged to avoid duplicates
        flagged: set[tuple[str, int]] = set()

        for event in events:
            if (
                event.type == "debuff_stack_apply"
                and event.ability_id == self.ability_id
                and event.target_name is not None
            ):
                stacks = (event.extra or {}).get("stack", 0)
                if stacks > self.max_safe_stacks:
                    key = (event.target_name, event.timestamp // 10000)  # Dedup within 10s window
                    if key not in flagged:
                        flagged.add(key)
                        evidence.append(
                            Evidence(
                                timestamp=event.timestamp,
                                type=EvidenceType.DEBUFF_STACK_EXCEEDED,
                                severity=self.severity,
                                player=event.target_name,
                                description=(
                                    f"{self.ability_name} 層數達到 {stacks} 層"
                                    f"（安全上限 {self.max_safe_stacks} 層）"
                                ),
                                details={
                                    "ability_id": self.ability_id,
                                    "ability_name": self.ability_name,
                                    "current_stacks": stacks,
                                    "max_safe_stacks": self.max_safe_stacks,
                                    "rule": self.name,
                                },
                            )
                        )

        return evidence

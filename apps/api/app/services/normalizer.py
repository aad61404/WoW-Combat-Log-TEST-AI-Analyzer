"""
Event Normalizer — converts raw WCL event data to NormalizedEvent models.

This is a pure function with no side effects:
- Resolves actor IDs to names
- Converts timestamps to fight-relative
- Maps WCL event type names to our internal type names
- Extracts relevant extra fields (stacks, overkill, overheal, etc.)
"""

from __future__ import annotations

from app.models.schemas import Actor, NormalizedEvent

# WCL event type → our normalized type
_TYPE_MAP: dict[str, str] = {
    "damage": "damage",
    "heal": "heal",
    "death": "death",
    "cast": "cast",
    "begincast": "begin_cast",
    "interrupt": "interrupt",
    "applydebuff": "debuff_apply",
    "refreshdebuff": "debuff_refresh",
    "removedebuff": "debuff_remove",
    "applydebuffstack": "debuff_stack_apply",
    "removedebuffstack": "debuff_stack_remove",
    "applybuff": "buff_apply",
    "removebuff": "buff_remove",
}

# Ability ID → Ability name cache (filled from fixture or WCL data)
_ABILITY_NAMES: dict[int, str] = {}


def set_ability_names(ability_map: dict[int | str, str]) -> None:
    """Pre-load ability names from an external source (e.g., fixture _abilityMap)."""
    _ABILITY_NAMES.clear()
    for k, v in ability_map.items():
        _ABILITY_NAMES[int(k)] = v


def normalize_events(
    raw_events: list[dict],
    actors: list[Actor],
    fight_start_time: int,
    ability_map: dict[int | str, str] | None = None,
) -> list[NormalizedEvent]:
    """
    Convert raw WCL events to normalized events.

    Args:
        raw_events: Raw event dicts from WCL GraphQL API.
        actors: Actor list for resolving sourceID/targetID to names.
        fight_start_time: The fight's startTime (ms, report-relative).
            All output timestamps will be relative to this value.
        ability_map: Optional mapping of abilityGameID → ability name.
            If provided, overrides the global _ABILITY_NAMES cache.

    Returns:
        List of NormalizedEvent, sorted by timestamp.
    """
    if ability_map is not None:
        set_ability_names(ability_map)

    # Build actor lookup: id → Actor
    actor_lookup: dict[int, Actor] = {a.id: a for a in actors}

    normalized: list[NormalizedEvent] = []

    for raw in raw_events:
        wcl_type = raw.get("type", "")
        our_type = _TYPE_MAP.get(wcl_type)
        if our_type is None:
            continue  # Skip unknown event types

        timestamp = raw.get("timestamp", 0) - fight_start_time

        # Resolve source
        source_id = raw.get("sourceID")
        source_actor = actor_lookup.get(source_id) if source_id else None

        # Resolve target
        target_id = raw.get("targetID")
        target_actor = actor_lookup.get(target_id) if target_id else None

        # Resolve ability name
        ability_id = raw.get("abilityGameID")
        ability_name = None
        if ability_id is not None:
            ability_name = _ABILITY_NAMES.get(int(ability_id))

        # For death events, the killing ability may be in a different field
        killing_ability_id = raw.get("killingAbilityGameID")
        if our_type == "death" and killing_ability_id:
            ability_id = killing_ability_id
            ability_name = _ABILITY_NAMES.get(int(killing_ability_id))

        # Build extra dict with any additional fields
        extra: dict = {}
        for field in ("overkill", "overheal", "absorbed", "stack", "hitType",
                      "extraAbilityGameID", "sourceInstance"):
            if field in raw:
                extra[field] = raw[field]

        normalized.append(
            NormalizedEvent(
                timestamp=timestamp,
                type=our_type,
                source_id=source_id,
                source_name=source_actor.name if source_actor else None,
                target_id=target_id,
                target_name=target_actor.name if target_actor else None,
                ability_id=ability_id,
                ability_name=ability_name,
                amount=raw.get("amount"),
                extra=extra,
            )
        )

    # Sort by timestamp
    normalized.sort(key=lambda e: e.timestamp)
    return normalized

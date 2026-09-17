"""Tests for the event normalizer."""

import json
from pathlib import Path

from app.models.schemas import Actor
from app.services.normalizer import normalize_events

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _get_actors() -> list[Actor]:
    """Get actors from sample_report.json."""
    report_data = _load_fixture("sample_report.json")
    actors_raw = report_data["data"]["reportData"]["report"]["masterData"]["actors"]
    return [
        Actor(
            id=a["id"],
            name=a["name"],
            type=a["type"],
            sub_type=a.get("subType", ""),
            server=a.get("server"),
        )
        for a in actors_raw
    ]


def _get_events_and_ability_map() -> tuple[list[dict], dict]:
    """Get raw events and ability map from sample_events.json."""
    data = _load_fixture("sample_events.json")
    raw_events = data["data"]["reportData"]["report"]["events"]["data"]
    ability_map = data.get("_abilityMap", {})
    return raw_events, ability_map


class TestNormalizer:
    """Test the event normalizer with fixture data."""

    def test_normalize_produces_events(self):
        """Normalizer should produce a non-empty list of events."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000  # From sample_report.json fight 1

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        assert len(events) > 0

    def test_timestamps_are_fight_relative(self):
        """All timestamps should be relative to fight start (>= 0)."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        for event in events:
            assert event.timestamp >= 0, f"Negative timestamp: {event.timestamp}"

    def test_actor_names_resolved(self):
        """Source and target names should be resolved from actor IDs."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        # Find a damage event — should have source and target names
        damage_events = [e for e in events if e.type == "damage"]
        assert len(damage_events) > 0

        # The boss (Ulgrax) should be resolved as source
        boss_damage = [e for e in damage_events if e.source_name == "Ulgrax the Devourer"]
        assert len(boss_damage) > 0

    def test_ability_names_resolved(self):
        """Ability names should be resolved from the ability map."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        # Find events with known abilities
        named_events = [e for e in events if e.ability_name is not None]
        assert len(named_events) > 0

        ability_names = {e.ability_name for e in named_events}
        assert "Digestive Acid" in ability_names
        assert "Savage Charge" in ability_names

    def test_death_events_have_killing_blow(self):
        """Death events should have ability_name set to the killing blow."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        death_events = [e for e in events if e.type == "death"]
        assert len(death_events) == 4  # 4 deaths in fixture

        # All deaths should have target names
        for death in death_events:
            assert death.target_name is not None

    def test_type_mapping(self):
        """WCL event types should be mapped to our internal types."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        types_found = {e.type for e in events}

        # These types should be present in our fixture
        assert "damage" in types_found
        assert "death" in types_found
        assert "heal" in types_found
        assert "begin_cast" in types_found
        assert "interrupt" in types_found
        assert "debuff_apply" in types_found
        assert "debuff_stack_apply" in types_found

    def test_events_sorted_by_timestamp(self):
        """Output events should be sorted by timestamp."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        for i in range(1, len(events)):
            assert events[i].timestamp >= events[i - 1].timestamp

    def test_extra_fields_preserved(self):
        """Extra fields (stacks, overheal, etc.) should be in the extra dict."""
        actors = _get_actors()
        raw_events, ability_map = _get_events_and_ability_map()
        fight_start_time = 60000

        events = normalize_events(raw_events, actors, fight_start_time, ability_map)

        # Find a debuff stack event
        stack_events = [e for e in events if e.type == "debuff_stack_apply"]
        assert len(stack_events) > 0
        assert stack_events[0].extra is not None
        assert "stack" in stack_events[0].extra

        # Find a heal event with overheal
        heal_events = [e for e in events if e.type == "heal"]
        assert len(heal_events) > 0
        heal_with_overheal = [e for e in heal_events if e.extra and "overheal" in e.extra]
        assert len(heal_with_overheal) > 0

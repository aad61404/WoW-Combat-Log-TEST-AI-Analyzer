"""Tests for the deterministic combat analyzer."""

import json
from pathlib import Path

from app.models.schemas import Actor, EvidenceType, FightSummary
from app.services.analyzer import CombatAnalyzer
from app.services.encounter_rules import get_rules_for_encounter
from app.services.normalizer import normalize_events

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _setup_fight_data():
    """Load fixtures and normalize events for fight 1 (Ulgrax wipe)."""
    report_data = _load_fixture("sample_report.json")
    events_data = _load_fixture("sample_events.json")

    actors_raw = report_data["data"]["reportData"]["report"]["masterData"]["actors"]
    actors = [
        Actor(
            id=a["id"],
            name=a["name"],
            type=a["type"],
            sub_type=a.get("subType", ""),
            server=a.get("server"),
        )
        for a in actors_raw
    ]

    fight = FightSummary(
        id=1,
        name="Ulgrax the Devourer",
        start_time=60000,
        end_time=452000,
        kill=False,
        difficulty=5,
        encounter_id=2902,
        fight_percentage=34.2,
    )

    raw_events = events_data["data"]["reportData"]["report"]["events"]["data"]
    ability_map = events_data.get("_abilityMap", {})

    normalized = normalize_events(raw_events, actors, fight.start_time, ability_map)
    rules = get_rules_for_encounter(fight.encounter_id)

    return fight, normalized, rules


class TestCombatAnalyzer:
    """Test the deterministic combat analyzer."""

    def test_analyze_produces_result(self):
        """Analyzer should produce a valid AnalysisResult."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        assert result is not None
        assert result.fight == fight
        assert result.fight_duration_seconds > 0

    def test_death_count(self):
        """Should detect the correct number of deaths."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        # Fixture has 4 deaths: ArmsWarr, FrostMage, HolyPriest, DemoLock
        assert result.total_deaths == 4

    def test_death_details(self):
        """Each death should have player name and pre-death damage."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        dead_players = {d.player for d in result.deaths}
        assert "ArmsWarr" in dead_players
        assert "FrostMage" in dead_players
        assert "HolyPriest" in dead_players
        assert "DemoLock" in dead_players

        # Each death should have at least some pre-death damage
        for death in result.deaths:
            assert death.player is not None
            assert death.timestamp > 0

    def test_death_pre_damage_window(self):
        """Deaths should include damage taken in the 5s window before death."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        # ArmsWarr dies at timestamp 110500 (relative: 50500)
        # Should have damage entries from ~45500 to 50500
        arms_death = next(d for d in result.deaths if d.player == "ArmsWarr")
        assert len(arms_death.damage_taken_last_5s) > 0

    def test_avoidable_damage_evidence(self):
        """Should detect avoidable damage from Digestive Acid."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        mechanic_fails = [
            e for e in result.evidence
            if e.type == EvidenceType.MECHANIC_FAIL
        ]

        # Digestive Acid hits FrostMage and DemoLock in the fixture
        assert len(mechanic_fails) > 0
        fail_players = {e.player for e in mechanic_fails}
        assert "FrostMage" in fail_players or "DemoLock" in fail_players

    def test_missed_interrupt_evidence(self):
        """Should detect the missed interrupt on Hungering Bellows."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        missed_interrupts = [
            e for e in result.evidence
            if e.type == EvidenceType.MISSED_INTERRUPT
        ]

        # The second Hungering Bellows (at ~253500) is not interrupted
        assert len(missed_interrupts) >= 1

    def test_debuff_stack_evidence(self):
        """Should detect Venomous Lash stack exceeding threshold."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        stack_evidence = [
            e for e in result.evidence
            if e.type == EvidenceType.DEBUFF_STACK_EXCEEDED
        ]

        # ArmsWarr gets 3 stacks (max safe = 2)
        assert len(stack_evidence) >= 1
        assert any(e.player == "ArmsWarr" for e in stack_evidence)

    def test_evidence_sorted_by_timestamp(self):
        """All evidence should be sorted by timestamp."""
        fight, events, rules = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, rules)

        for i in range(1, len(result.evidence)):
            assert result.evidence[i].timestamp >= result.evidence[i - 1].timestamp

    def test_analyze_without_rules(self):
        """Analyzer should still work without encounter rules (death analysis only)."""
        fight, events, _ = _setup_fight_data()
        analyzer = CombatAnalyzer()

        result = analyzer.analyze(fight, events, encounter_rules=None)

        # Should still have deaths
        assert result.total_deaths == 4
        # But only death evidence, no mechanic fails
        non_death = [e for e in result.evidence if e.type != EvidenceType.DEATH]
        assert len(non_death) == 0

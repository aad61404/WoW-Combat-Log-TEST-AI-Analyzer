"""Tests for The Venomous Abyss encounter rules."""

from app.models.schemas import EvidenceType, NormalizedEvent, Severity
from app.services.encounter_rules import ENCOUNTER_RULES, get_rules_for_encounter
from app.services.encounter_rules.venomous_abyss import VENOMOUS_ABYSS_RULES

NEKZALI = 3470
ENTOMBED_SENTINELS = 3445
VASHNIK = 3455
ULATEK = 3492
VICIOUS_ECHOES = 1310764
CAUSTIC_WAVES = 1292403


def test_registry_includes_venomous_abyss_without_replacing_existing():
    assert set(VENOMOUS_ABYSS_RULES) <= set(ENCOUNTER_RULES)
    assert get_rules_for_encounter(2902)  # Ulgrax (Nerub-ar Palace) still registered


def test_bosses_without_qualifying_mechanics_have_no_rules():
    assert get_rules_for_encounter(ENTOMBED_SENTINELS) == []
    assert get_rules_for_encounter(VASHNIK) == []


def test_ability_ids_are_unique_per_encounter():
    for rules in VENOMOUS_ABYSS_RULES.values():
        ids = [r.ability_id for r in rules]
        assert len(ids) == len(set(ids))


def test_missed_vicious_echoes_is_critical():
    events = [
        NormalizedEvent(timestamp=1000, type="begin_cast", source_name="Shrieker", ability_id=VICIOUS_ECHOES),
        NormalizedEvent(timestamp=3000, type="cast", source_name="Shrieker", ability_id=VICIOUS_ECHOES),
    ]
    evidence = [e for r in get_rules_for_encounter(ULATEK) for e in r.evaluate(events)]

    assert len(evidence) == 1
    assert evidence[0].type == EvidenceType.MISSED_INTERRUPT
    assert evidence[0].severity == Severity.CRITICAL


def test_caustic_waves_hit_is_mechanic_fail():
    events = [
        NormalizedEvent(timestamp=5000, type="damage", target_name="PlayerA", ability_id=CAUSTIC_WAVES, amount=120000),
    ]
    evidence = [e for r in get_rules_for_encounter(ULATEK) for e in r.evaluate(events)]

    assert [(e.type, e.player) for e in evidence] == [(EvidenceType.MECHANIC_FAIL, "PlayerA")]


def test_nekzali_rules_ignore_unrelated_damage():
    events = [
        NormalizedEvent(timestamp=5000, type="damage", target_name="PlayerA", ability_id=999999, amount=50000),
    ]
    assert [e for r in get_rules_for_encounter(NEKZALI) for e in r.evaluate(events)] == []

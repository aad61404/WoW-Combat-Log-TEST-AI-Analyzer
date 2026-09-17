"""
Encounter Rule Registry — maps encounter IDs to their analysis rules.

Boss-specific rules are defined here. Each boss entry lists the rules
that apply to that encounter, with concrete ability IDs and thresholds.

For bosses without defined rules, the analyzer still produces
death timeline analysis — just without mechanic_fail evidence.
"""

from __future__ import annotations

from .base import EncounterRule
from .generic import AvoidableDamageRule, DebuffStackRule, InterruptRule

# =============================================================================
# Boss Rule Definitions
#
# Format: encounter_id → list of EncounterRule
#
# To add a new boss:
# 1. Find the encounterID from WCL (visible in the GraphQL response)
# 2. Identify avoidable abilities, interruptible casts, and dangerous debuffs
# 3. Add an entry below with the appropriate rules
# =============================================================================

ENCOUNTER_RULES: dict[int, list[EncounterRule]] = {
    # -------------------------------------------------------------------------
    # Nerub-ar Palace — The War Within Season 2
    # -------------------------------------------------------------------------

    # Ulgrax the Devourer (encounterID: 2902)
    # - Digestive Acid (435136): AoE that players should spread to avoid
    # - Hungering Bellows (441465): Interruptible cast, heavy raid damage if not kicked
    # - Venomous Lash (434803): Debuff stacks, must swap/drop at 2 stacks
    2902: [
        AvoidableDamageRule(
            ability_id=435136,
            ability_name="Digestive Acid",
        ),
        InterruptRule(
            ability_id=441465,
            ability_name="Hungering Bellows",
        ),
        DebuffStackRule(
            ability_id=434803,
            ability_name="Venomous Lash",
            max_safe_stacks=2,
        ),
    ],

    # The Bloodbound Horror (encounterID: 2917)
    # - Gruesome Disgorge (442530): Frontal cone, avoidable
    # - Black Blooded (443612): Interruptible add cast
    # - Bloodcurdle (445936): Debuff stacks, dangerous above 3
    2917: [
        AvoidableDamageRule(
            ability_id=442530,
            ability_name="Gruesome Disgorge",
        ),
        InterruptRule(
            ability_id=443612,
            ability_name="Black Blooded",
        ),
        DebuffStackRule(
            ability_id=445936,
            ability_name="Bloodcurdle",
            max_safe_stacks=3,
        ),
    ],
}


def get_rules_for_encounter(encounter_id: int) -> list[EncounterRule]:
    """
    Get the analysis rules for a specific encounter.

    Returns an empty list for encounters without defined rules.
    The analyzer will still produce death timeline analysis.
    """
    return ENCOUNTER_RULES.get(encounter_id, [])


__all__ = [
    "EncounterRule",
    "AvoidableDamageRule",
    "InterruptRule",
    "DebuffStackRule",
    "ENCOUNTER_RULES",
    "get_rules_for_encounter",
]

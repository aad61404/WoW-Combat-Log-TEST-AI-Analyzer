"""
The Venomous Abyss — Midnight Season 2 (WCL zone 54).

Sources (2026-09-28):
- Encounter IDs: wago.tools DungeonEncounter (MapID 3004), cross-checked with WCL URLs
  (Nek'zali = 3470, Entombed Sentinels = 53445 → 3445).
- Mechanics: mythictrap.com/en/venomous-abyss/<boss>. Spell names verified against wago.tools SpellName.

Only mechanics the guide explicitly marks as dodge or must-interrupt are included.
No DebuffStackRule: no guide states a numeric safe stack count.
Entombed Sentinels (3445) and Vashnik the Malignant (3455) have no rule that meets that bar.

Unverified against real logs: guide spell IDs may differ from the damage/cast IDs WCL records.
"""

from __future__ import annotations

from app.models.schemas import Severity

from .base import EncounterRule
from .generic import AvoidableDamageRule, InterruptRule

VENOMOUS_ABYSS_RULES: dict[int, list[EncounterRule]] = {
    # Nek'zali the Soulcoiler
    3470: [
        AvoidableDamageRule(ability_id=1292248, ability_name="Soul Transfer"),
    ],
    # The Lost Explorers
    3497: [
        AvoidableDamageRule(ability_id=1292388, ability_name="Evil Eyes"),
        # Guide: "Interrupt or dispel" — a missed kick is recoverable.
        InterruptRule(ability_id=1286921, ability_name="Icebound Flames", severity=Severity.INFO),
    ],
    # Sszorak
    3420: [
        AvoidableDamageRule(ability_id=1287072, ability_name="Tempest"),
    ],
    # The Twin Fangs
    3421: [
        AvoidableDamageRule(ability_id=1294293, ability_name="Vile Flood"),
        AvoidableDamageRule(ability_id=1306872, ability_name="Sanguine Storm"),
    ],
    # The Coiled Altar
    3429: [
        AvoidableDamageRule(ability_id=1283832, ability_name="Axegrinder"),
    ],
    # Ula'tek
    3492: [
        AvoidableDamageRule(ability_id=1292403, ability_name="Caustic Waves"),
        AvoidableDamageRule(ability_id=1302982, ability_name="Virulent Spit"),
        InterruptRule(ability_id=1290779, ability_name="Malice"),
        InterruptRule(ability_id=1305650, ability_name="Anguished Cry"),
        # Guide: "Always interrupt this cast or you will wipe."
        InterruptRule(ability_id=1310764, ability_name="Vicious Echoes", severity=Severity.CRITICAL),
    ],
}

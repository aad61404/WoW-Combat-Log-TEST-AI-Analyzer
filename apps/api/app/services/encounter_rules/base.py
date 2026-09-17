"""
Encounter Rule Engine — Base classes.

Each rule evaluates a list of normalized events and returns
deterministic evidence. Rules do not guess — they check
explicit conditions (e.g., "this ability ID hit a player"
means a mechanic failure, because we know that ability is avoidable).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import Evidence, NormalizedEvent


class EncounterRule(ABC):
    """Abstract base class for encounter-specific analysis rules."""

    name: str
    description: str

    @abstractmethod
    def evaluate(self, events: list[NormalizedEvent]) -> list[Evidence]:
        """
        Evaluate normalized events and return evidence of issues found.

        Returns:
            List of Evidence objects. Empty list if no issues detected.
        """
        ...

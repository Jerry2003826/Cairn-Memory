"""Dogfood cold-vs-warm improvement decision logic.

Extracted from ``eval.classify.evaluate_dogfood`` (was CC=21) so the
improvement / summary decision is a set of small pure functions, kept in
its own submodule to keep ``classify.py`` under its line budget.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DogfoodSignals:
    """Pre-computed cold-vs-warm comparison signals for a dogfood run pair."""

    cold_comparable: bool
    warm_executed_expected: bool
    command_adopted: bool
    rediscovery_improved: bool
    position_improved: bool
    machine_read_recovery_improved: bool


def is_improvement(sig: DogfoodSignals) -> bool:
    if not sig.cold_comparable:
        return False
    executed_with_signal = sig.warm_executed_expected and (
        sig.command_adopted or sig.rediscovery_improved or sig.position_improved
    )
    return bool(executed_with_signal or sig.machine_read_recovery_improved)


def improvement_summary(sig: DogfoodSignals, *, improvement: bool) -> str:
    if not sig.cold_comparable:
        return "cold run not comparable"
    if sig.machine_read_recovery_improved and not sig.warm_executed_expected:
        return "warm used machine-read surfaces and reduced rediscovery"
    if improvement:
        return "warm adopted expected command or reduced rediscovery"
    return "no measurable warm-run improvement"

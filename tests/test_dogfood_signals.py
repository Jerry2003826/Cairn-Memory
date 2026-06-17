"""Unit tests for the extracted dogfood improvement helpers.

evaluate_dogfood was CC=21; the improvement/summary decision logic is
extracted into pure helpers (_DogfoodSignals + _is_improvement +
_improvement_summary) so each piece is independently testable and the
main function's complexity drops.
"""

from __future__ import annotations

from omni.eval.classify import (
    _DogfoodSignals,
    _improvement_summary,
    _is_improvement,
)


def _signals(**overrides) -> _DogfoodSignals:
    base = dict(
        cold_comparable=True,
        warm_executed_expected=True,
        command_adopted=False,
        rediscovery_improved=False,
        position_improved=False,
        machine_read_recovery_improved=False,
    )
    base.update(overrides)
    return _DogfoodSignals(**base)


# --- _is_improvement -------------------------------------------------------

def test_not_improvement_when_cold_not_comparable() -> None:
    assert _is_improvement(_signals(cold_comparable=False, command_adopted=True)) is False


def test_improvement_when_warm_executed_and_command_adopted() -> None:
    assert _is_improvement(_signals(command_adopted=True)) is True


def test_improvement_when_warm_executed_and_rediscovery_improved() -> None:
    assert _is_improvement(_signals(rediscovery_improved=True)) is True


def test_improvement_when_warm_executed_and_position_improved() -> None:
    assert _is_improvement(_signals(position_improved=True)) is True


def test_not_improvement_when_warm_did_not_execute_expected() -> None:
    # command_adopted alone is not enough without executing the expected cmd
    assert _is_improvement(
        _signals(warm_executed_expected=False, command_adopted=True)
    ) is False


def test_improvement_via_machine_read_recovery_even_without_execution() -> None:
    assert _is_improvement(
        _signals(warm_executed_expected=False, machine_read_recovery_improved=True)
    ) is True


# --- _improvement_summary --------------------------------------------------

def test_summary_when_not_comparable() -> None:
    sig = _signals(cold_comparable=False)
    assert _improvement_summary(sig, improvement=False) == "cold run not comparable"


def test_summary_machine_read_recovery_without_execution() -> None:
    sig = _signals(warm_executed_expected=False, machine_read_recovery_improved=True)
    assert (
        _improvement_summary(sig, improvement=True)
        == "warm used machine-read surfaces and reduced rediscovery"
    )


def test_summary_generic_improvement() -> None:
    sig = _signals(command_adopted=True)
    assert (
        _improvement_summary(sig, improvement=True)
        == "warm adopted expected command or reduced rediscovery"
    )


def test_summary_no_improvement() -> None:
    sig = _signals()
    assert (
        _improvement_summary(sig, improvement=False)
        == "no measurable warm-run improvement"
    )

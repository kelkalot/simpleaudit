"""
Tests for per-call generation params (temperature, top_p, max_tokens, etc.).

Run with: pytest tests/test_generation_params.py -v
"""

import asyncio
import pytest

from tests.fakes import make_auditor, fixed_target, fixed_severity_judge, fixed_probe_auditor


class CapturingClient:
    """Fake client that records every acompletion kwargs dict."""

    def __init__(self, text: str = "ok") -> None:
        self.text = text
        self.calls: list[dict] = []

    async def acompletion(self, **kwargs):
        self.calls.append(kwargs)
        import types
        msg = types.SimpleNamespace(content=self.text)
        choice = types.SimpleNamespace(message=msg)
        usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1)
        return types.SimpleNamespace(choices=[choice], usage=usage)


def test_run_scenario_passes_params_to_target():
    """params on run_scenario reach the target's acompletion call."""
    target = CapturingClient("I cannot help with that.")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)

    params = {"temperature": 0.7, "max_tokens": 2048}
    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
            params=params,
        )
    )

    # The target call is the one whose model is "fake-model"
    target_calls = [c for c in target.calls]
    assert len(target_calls) == 1
    assert target_calls[0].get("temperature") == 0.7
    assert target_calls[0].get("max_tokens") == 2048


def test_run_scenario_params_reach_judge():
    """params on run_scenario also reach the judge's acompletion call."""
    target = fixed_target("I cannot help with that.")
    judge = CapturingClient()
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)

    params = {"top_p": 0.9}
    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
            params=params,
        )
    )

    assert len(judge.calls) == 1
    assert judge.calls[0].get("top_p") == 0.9


def test_run_scenario_no_params_is_noop():
    """Without params, acompletion kwargs are unchanged (no extra keys)."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
        )
    )

    for call in target.calls:
        assert "temperature" not in call
        assert "max_tokens" not in call
        assert "top_p" not in call


def test_run_async_passes_params():
    """params on run_async propagate to run_scenario and reach acompletion."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)

    params = {"temperature": 0.3, "chat_template_kwargs": {"enable_thinking": False}}
    asyncio.run(
        ma.run_async(
            scenarios=[{"name": "Test", "description": "A test scenario."}],
            params=params,
        )
    )

    assert len(target.calls) == 1
    assert target.calls[0].get("temperature") == 0.3
    assert target.calls[0].get("chat_template_kwargs") == {"enable_thinking": False}


def test_run_scenario_params_override_constructor_defaults():
    """Per-call params override constructor-level defaults."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)
    # Simulate constructor-level defaults
    ma._default_params = {"temperature": 0.5, "max_tokens": 100}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
            params={"temperature": 0.9},
        )
    )

    assert target.calls[0].get("temperature") == 0.9
    assert target.calls[0].get("max_tokens") == 100  # inherited from defaults


def test_run_scenario_uses_constructor_defaults_when_no_params():
    """Constructor-level defaults apply when no per-call params given."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)
    ma._default_params = {"temperature": 0.5}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
        )
    )

    assert target.calls[0].get("temperature") == 0.5


def test_target_params_apply_only_to_target():
    """target_params reach the target but not the judge."""
    target = CapturingClient("ok")
    judge = CapturingClient()
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)
    ma._default_target_params = {"temperature": 0.1}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
        )
    )

    assert target.calls[0].get("temperature") == 0.1
    assert "temperature" not in judge.calls[0]


def test_judge_params_apply_only_to_judge():
    """judge_params reach the judge but not the target."""
    target = CapturingClient("ok")
    judge = CapturingClient()
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)
    ma._default_judge_params = {"temperature": 0.0}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
        )
    )

    assert judge.calls[0].get("temperature") == 0.0
    assert "temperature" not in target.calls[0]


def test_auditor_params_apply_only_to_auditor():
    """auditor_params reach the auditor but not the target or judge."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = CapturingClient("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=2)
    ma._default_auditor_params = {"temperature": 1.0}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
        )
    )

    # Turn 0 uses test_prompt (no auditor call); turn 1 calls the auditor.
    assert len(auditor.calls) == 1
    assert auditor.calls[0].get("temperature") == 1.0
    assert "temperature" not in target.calls[0]


def test_per_call_role_params_override_constructor_role_defaults():
    """Per-call target_params override constructor target_params."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)
    ma._default_target_params = {"temperature": 0.1, "max_tokens": 500}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
            target_params={"temperature": 0.8},
        )
    )

    assert target.calls[0].get("temperature") == 0.8
    assert target.calls[0].get("max_tokens") == 500  # inherited from role default


def test_base_params_merge_with_role_params():
    """Base params and role params merge; role wins on conflict."""
    target = CapturingClient("ok")
    judge = fixed_severity_judge("pass")
    auditor = fixed_probe_auditor("Tell me more.")
    ma = make_auditor(target=target, judge=judge, auditor=auditor, max_turns=1)
    ma._default_params = {"temperature": 0.5, "max_tokens": 1000}
    ma._default_target_params = {"temperature": 0.2}

    asyncio.run(
        ma.run_scenario(
            name="Test",
            description="A test scenario.",
            test_prompt="Hello",
        )
    )

    assert target.calls[0].get("temperature") == 0.2  # role wins
    assert target.calls[0].get("max_tokens") == 1000  # from base

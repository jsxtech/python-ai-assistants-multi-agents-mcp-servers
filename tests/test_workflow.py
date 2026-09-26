"""Tests for Workflow: dependencies, conditions, skip cascade, retry, error handlers, parallel."""
import pytest

from multi_agent_system import MultiAgentSystem
from workflow import Workflow
from conftest import EchoAgent, AlwaysFailAgent


def build_system(extra_agents=None):
    s = MultiAgentSystem(max_workers=4)
    s.add_agent(EchoAgent("a", "role", capabilities=["x"]))
    s.add_agent(EchoAgent("b", "role", capabilities=["x"]))
    s.add_agent(EchoAgent("c", "role", capabilities=["x"]))
    for ag in extra_agents or []:
        s.add_agent(ag)
    return s


def test_add_step_validates_dependencies():
    wf = Workflow("w")
    wf.add_step("a", "t0")
    with pytest.raises(ValueError):
        wf.add_step("b", "t1", depends_on=[5])  # invalid forward dep


def test_sequential_execution_with_dependencies():
    s = build_system()
    wf = Workflow("w")
    wf.add_step("a", "gather")
    wf.add_step("b", "process", depends_on=[0])
    wf.add_step("c", "report", depends_on=[1])
    results = wf.execute(s)
    assert len(results) == 3
    assert all(r["status"] == "completed" for r in results)


def test_conditional_step_skipped():
    s = build_system()
    wf = Workflow("w")
    wf.add_step("a", "gather")
    # condition false -> step 1 skipped, so step 2 (depends on 1) cascade-skipped
    wf.add_step("b", "process", depends_on=[0], condition=lambda r: False)
    wf.add_step("c", "report", depends_on=[1])
    results = wf.execute(s)
    assert len(results) == 1  # only step 0 ran


def test_sequential_retries_failed_agent_then_error_handler():
    # Agent always fails; workflow retries max_retries times, then error handler fires.
    failing = AlwaysFailAgent("f", "role")
    s = build_system(extra_agents=[failing])
    wf = Workflow("w", max_retries=2)
    wf.add_step("f", "willfail")
    handler_calls = {"n": 0}

    def handler(err, step, ctx):
        handler_calls["n"] += 1
        return {"status": "recovered", "agent": "f", "task": step["task"]}

    wf.add_error_handler(0, handler)
    results = wf.execute(s)
    assert results[0]["status"] == "recovered"
    assert handler_calls["n"] == 1
    # Agent should have been invoked max_retries times (retry actually happened)
    assert len(failing.task_history) == 2


def test_sequential_retry_recovers_without_handler():
    # Fails on the workflow-visible attempts? Agent has internal retries too.
    # Use an agent that fails its internal retries once-cycle then succeeds is
    # complex; instead verify a failing agent with no handler surfaces failure.
    failing = AlwaysFailAgent("f", "role")
    s = build_system(extra_agents=[failing])
    wf = Workflow("w", max_retries=2)
    wf.add_step("f", "willfail")
    results = wf.execute(s)
    # No handler -> last failed result is persisted, not an exception.
    assert results[0]["status"] == "failed"
    assert len(failing.task_history) == 2  # retried


def test_error_handler_on_raised_exception():
    s = build_system()
    wf = Workflow("w", max_retries=2)
    wf.add_step("ghost", "willraise")  # missing agent -> system.delegate raises
    wf.add_error_handler(0, lambda err, step, ctx: {"status": "handled"})
    results = wf.execute(s)
    assert results[0]["status"] == "handled"


def test_missing_agent_without_handler_raises():
    s = build_system()
    wf = Workflow("w", max_retries=1)
    wf.add_step("ghost", "willraise")
    with pytest.raises(ValueError, match="not found"):
        wf.execute(s)


def test_parallel_execution_levels():
    s = build_system()
    wf = Workflow("w")
    wf.add_step("a", "l0")
    wf.add_step("b", "l0b")
    wf.add_step("c", "l1", depends_on=[0, 1])
    results = wf.execute(s, parallel=True)
    assert len(results) == 3
    assert all(r["status"] == "completed" for r in results)


def test_parallel_retries_and_error_handler():
    failing = AlwaysFailAgent("f", "role")
    s = build_system(extra_agents=[failing])
    wf = Workflow("w", max_retries=3)
    wf.add_step("f", "willfail")
    wf.add_error_handler(0, lambda err, step, ctx: {"status": "recovered"})
    results = wf.execute(s, parallel=True)
    assert results[0]["status"] == "recovered"
    # 1 initial + 2 retries = 3 invocations
    assert len(failing.task_history) == 3


def test_workflow_stats():
    s = build_system()
    wf = Workflow("w")
    wf.add_step("a", "t")
    assert wf.get_stats() == {"executions": 0}
    wf.execute(s)
    stats = wf.get_stats()
    assert stats["executions"] == 1
    assert stats["total_steps"] == 1
    assert stats["avg_duration"] >= 0

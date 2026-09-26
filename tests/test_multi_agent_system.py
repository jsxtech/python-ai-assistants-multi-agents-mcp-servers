"""Tests for MultiAgentSystem: delegation, parallel ordering/timeout, shared memory, leaderboard."""
import time

import pytest

from multi_agent_system import MultiAgentSystem
from conftest import EchoAgent, AlwaysFailAgent


def build_system():
    s = MultiAgentSystem(max_workers=4)
    s.add_agent(EchoAgent("a1", "role", capabilities=["cap", "shared"], priority=1))
    s.add_agent(EchoAgent("a2", "role", capabilities=["shared"], priority=5))
    return s


def test_delegate_and_missing_agent():
    s = build_system()
    r = s.delegate("a1", "hello")
    assert r["status"] == "completed"
    with pytest.raises(ValueError):
        s.delegate("ghost", "x")


def test_middleware_transforms_task():
    s = build_system()
    s.add_middleware(lambda name, task, ctx: (task.upper(), ctx))
    r = s.delegate("a1", "hi")
    assert r["result"] == "done:HI"


def test_parallel_execute_preserves_order():
    s = build_system()
    tasks = [
        {"agent": "a1", "task": "first"},
        {"agent": "a2", "task": "second"},
        {"agent": "a1", "task": "third"},
    ]
    results = s.parallel_execute(tasks)
    assert [r["result"] for r in results] == ["done:first", "done:second", "done:third"]


def test_parallel_execute_empty():
    s = build_system()
    assert s.parallel_execute([]) == []


def test_parallel_execute_bad_agent_yields_error_entry():
    s = build_system()
    tasks = [{"agent": "a1", "task": "ok"}, {"agent": "ghost", "task": "x"}]
    results = s.parallel_execute(tasks)
    assert results[0]["status"] == "completed"
    assert results[1]["status"] == "error"


class SlowAgent(EchoAgent):
    def _execute(self, task, context=None):
        time.sleep(0.5)
        return "slow"


def test_parallel_execute_timeout_marks_incomplete():
    s = MultiAgentSystem(max_workers=2)
    s.add_agent(SlowAgent("slow", "role"))
    results = s.parallel_execute([{"agent": "slow", "task": "t"}], timeout=0.05)
    assert results[0]["status"] == "error"


def test_broadcast_hits_all_agents():
    s = build_system()
    results = s.broadcast("ping")
    assert len(results) == 2
    assert all(r["status"] == "completed" for r in results)


def test_find_and_best_agent_by_capability():
    s = build_system()
    caps = s.find_agent_by_capability("shared")
    assert {a.name for a in caps} == {"a1", "a2"}
    # a2 has higher priority
    assert s.get_best_agent("shared").name == "a2"
    with pytest.raises(ValueError):
        s.get_best_agent("nonexistent")


def test_auto_delegate_uses_best_agent():
    s = build_system()
    r = s.auto_delegate("do it", "shared")
    assert r["agent"] == "a2"


def test_shared_memory_and_ttl():
    s = build_system()
    s.share_data("k", "v")
    assert s.get_shared_data("k") == "v"
    s.share_data("expired", "x", ttl=-1)
    assert s.get_shared_data("expired") is None


def test_system_status_and_leaderboard():
    s = build_system()
    s.delegate("a1", "t")
    status = s.get_system_status()
    assert "a1" in status["agents"]
    assert status["active_agents"] == 0  # all idle after completion
    board = s.get_agent_leaderboard()
    assert len(board) == 2


def test_remove_agent():
    s = build_system()
    s.remove_agent("a1")
    with pytest.raises(ValueError):
        s.delegate("a1", "x")


class BlockingAgent(EchoAgent):
    """Agent that blocks in _execute until released, to observe concurrent state."""

    def __init__(self, *args, **kwargs):
        import threading as _t
        super().__init__(*args, **kwargs)
        self.entered = _t.Event()
        self.release = _t.Event()
        self.concurrent_active_seen = 0

    def _execute(self, task, context=None):
        self.entered.set()
        # Record how many process() calls are in flight while we're blocked.
        self.concurrent_active_seen = max(self.concurrent_active_seen, self._active)
        self.release.wait(timeout=2)
        return "done"


def test_same_agent_concurrent_state_counter():
    """Running the same agent concurrently must report 'busy' until ALL finish.

    A binary busy/idle flag would incorrectly flip to idle when the first task
    finished. The counter-based state must stay 'busy' until both complete.
    """
    import threading

    agent = BlockingAgent("blk", "role", capabilities=["cap"])
    s = MultiAgentSystem(max_workers=4)
    s.add_agent(agent)

    threads = [threading.Thread(target=lambda: s.delegate("blk", "t")) for _ in range(2)]
    for t in threads:
        t.start()

    # Wait until at least one task is executing.
    agent.entered.wait(timeout=2)
    # Give the second thread a moment to also enter process().
    time.sleep(0.05)
    assert agent.state == "busy"
    assert agent._active == 2  # both in flight simultaneously

    # Release and let them finish.
    agent.release.set()
    for t in threads:
        t.join(timeout=2)

    assert agent.state == "idle"
    assert agent._active == 0
    assert len(agent.task_history) == 2  # both recorded, no corruption
    assert agent.concurrent_active_seen == 2


def test_get_system_status_stable_under_concurrent_delegation():
    """get_system_status must not raise while agents are being delegated to."""
    import threading

    s = MultiAgentSystem(max_workers=4)
    for i in range(5):
        s.add_agent(EchoAgent(f"a{i}", "role", capabilities=["cap"]))

    stop = threading.Event()
    errors = []

    def hammer():
        while not stop.is_set():
            try:
                s.delegate("a0", "t")
                s.share_data("k", "v")
            except Exception as e:  # pragma: no cover
                errors.append(e)

    worker = threading.Thread(target=hammer)
    worker.start()
    try:
        for _ in range(100):
            status = s.get_system_status()
            assert "agents" in status
    finally:
        stop.set()
        worker.join(timeout=2)

    assert errors == []

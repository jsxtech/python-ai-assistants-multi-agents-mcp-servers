"""Tests for persistence: StateManager and MetricsCollector."""
import json
import os

from persistence import StateManager, MetricsCollector
from multi_agent_system import MultiAgentSystem
from conftest import EchoAgent


def build_system():
    s = MultiAgentSystem()
    agent = EchoAgent("a1", "role", capabilities=["cap"])
    agent.remember("k", "v")
    s.add_agent(agent)
    s.share_data("shared_key", "shared_val")
    return s


def test_save_and_load_state(tmp_path):
    s = build_system()
    fp = tmp_path / "state.json"
    mgr = StateManager(str(fp))
    mgr.save_state(s)
    assert fp.exists()
    loaded = mgr.load_state()
    assert "a1" in loaded["agents"]
    assert loaded["agents"]["a1"]["role"] == "role"
    assert "shared_key" in loaded["shared_memory_keys"]


def test_save_state_serializable(tmp_path):
    s = build_system()
    fp = tmp_path / "state.json"
    mgr = StateManager(str(fp))
    mgr.save_state(s)
    # Must be valid JSON (no circular reference errors)
    with open(fp) as f:
        json.load(f)


def test_load_missing_file_returns_empty(tmp_path):
    mgr = StateManager(str(tmp_path / "does_not_exist.json"))
    assert mgr.load_state() == {}


def test_checkpoint_and_restore(tmp_path):
    s = build_system()
    mgr = StateManager(str(tmp_path / "state.json"))
    mgr.checkpoint(s, "backup1")
    restored = mgr.restore_checkpoint("backup1")
    assert "a1" in restored["agents"]


def test_metrics_collector_records():
    mc = MetricsCollector()
    mc.record("a1", {"status": "completed", "duration": 0.1})
    mc.record("a1", {"status": "failed", "duration": 0.2})
    summary = mc.get_summary()
    assert summary["total_requests"] == 2
    assert summary["success_rate"] == 0.5
    assert summary["avg_duration"] > 0
    assert summary["agent_metrics"]["a1"]["successes"] == 1
    assert summary["agent_metrics"]["a1"]["failures"] == 1


def test_metrics_reset():
    mc = MetricsCollector()
    mc.record("a1", {"status": "completed", "duration": 0.1})
    mc.reset()
    assert mc.get_summary()["total_requests"] == 0

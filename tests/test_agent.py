"""Tests for Agent: memory/TTL, retry, metrics, callbacks, tools."""
import time

from agent import Agent
from conftest import EchoAgent, FailingAgent, AlwaysFailAgent


def test_process_success_records_completed():
    agent = EchoAgent("a", "role")
    result = agent.process("task1")
    assert result["status"] == "completed"
    assert result["result"] == "done:task1"
    assert result["retry_count"] == 0
    assert len(agent.task_history) == 1


def test_process_retries_then_succeeds():
    agent = FailingAgent("a", "role", fail_times=2)  # max_retries=3 -> attempts 0,1,2,3
    result = agent.process("t")
    assert result["status"] == "completed"
    assert result["retry_count"] == 2  # succeeded on 3rd call (attempt index 2)


def test_process_permanent_failure_reports_failed():
    agent = AlwaysFailAgent("a", "role")
    result = agent.process("t")
    assert result["status"] == "failed"
    assert "permanent failure" in result["error"]
    assert result["retry_count"] == agent.max_retries


def test_process_never_appends_none():
    agent = AlwaysFailAgent("a", "role")
    agent.process("t")
    assert all(entry is not None for entry in agent.task_history)
    assert all("status" in entry for entry in agent.task_history)


def test_memory_basic_and_forget():
    agent = EchoAgent("a", "role")
    agent.remember("k", "v")
    assert agent.recall("k") == "v"
    agent.forget("k")
    assert agent.recall("k") is None


def test_memory_ttl_expiry():
    agent = EchoAgent("a", "role")
    agent.remember("k", "v", ttl=-1)  # already expired
    assert agent.recall("k") is None
    assert "k" not in agent.memory  # cleaned up on access


def test_clear_memory():
    agent = EchoAgent("a", "role")
    agent.remember("a", 1)
    agent.remember("b", 2)
    agent.clear_memory()
    assert agent.recall("a") is None and agent.recall("b") is None


def test_metrics_success_rate():
    agent = FailingAgent("a", "role", fail_times=99)  # always fails within retries
    good = EchoAgent("b", "role")
    good.process("ok")
    good.process("ok2")
    m = good.get_metrics()
    assert m["total_tasks"] == 2
    assert m["completed"] == 2
    assert m["success_rate"] == 1.0
    assert m["avg_duration"] >= 0

    agent.process("bad")
    fm = agent.get_metrics()
    assert fm["failed"] == 1
    assert fm["success_rate"] == 0.0


def test_callbacks_invoked_and_bad_callback_isolated():
    agent = EchoAgent("a", "role")
    seen = []
    agent.add_callback(lambda r: seen.append(r["status"]))
    agent.add_callback(lambda r: (_ for _ in ()).throw(RuntimeError("bad cb")))
    result = agent.process("t")
    assert result["status"] == "completed"
    assert seen == ["completed"]  # first callback ran despite second raising


def test_use_tool_and_missing_server(mcp_server):
    agent = EchoAgent("a", "role", mcp_servers=[mcp_server])
    assert agent.use_tool("test_server", "read", {"path": "/x"}) == "content:/x"
    try:
        agent.use_tool("nope", "read", {"path": "/x"})
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_available_tools(mcp_server):
    agent = EchoAgent("a", "role", mcp_servers=[mcp_server])
    tools = agent.get_available_tools()
    assert "test_server" in tools
    assert set(tools["test_server"]) == {"read", "boom"}


def test_state_returns_to_idle():
    agent = EchoAgent("a", "role")
    agent.process("t")
    assert agent.state == "idle"

"""Tests for MCPServer: caching, hooks, error handling, rate-limit logging, stats."""
import pytest

from mcp_server import MCPServer


def make_server(rate_limit=None):
    s = MCPServer("srv", "desc", rate_limit=rate_limit)
    return s


def test_register_and_execute():
    s = make_server()
    s.register_tool("add", lambda a, b: a + b, "adds")
    assert s.execute("add", {"a": 2, "b": 3}) == 5


def test_execute_unknown_tool_raises():
    s = make_server()
    with pytest.raises(ValueError):
        s.execute("missing", {})


def test_caching_returns_same_result_without_recompute():
    s = make_server()
    calls = {"n": 0}

    def tool(path):
        calls["n"] += 1
        return f"content:{path}:{calls['n']}"

    s.register_tool("read", tool, cacheable=True)
    first = s.execute("read", {"path": "/a"})
    second = s.execute("read", {"path": "/a"})
    assert first == second
    assert calls["n"] == 1  # second served from cache

    s.clear_cache()
    third = s.execute("read", {"path": "/a"})
    assert calls["n"] == 2  # recomputed after cache clear
    assert third != first


def test_non_cacheable_always_recomputes():
    s = make_server()
    calls = {"n": 0}
    s.register_tool("t", lambda: calls.__setitem__("n", calls["n"] + 1) or calls["n"])
    s.execute("t", {})
    s.execute("t", {})
    assert calls["n"] == 2


def test_before_and_after_hooks_fire():
    s = make_server()
    s.register_tool("read", lambda path: f"c:{path}")
    before, after = [], []
    s.add_hook("before", lambda name, params: before.append(name))
    s.add_hook("after", lambda entry: after.append(entry["status"]))
    s.execute("read", {"path": "/x"})
    assert before == ["read"]
    assert after == ["success"]


def test_tool_error_raises_and_logs():
    s = make_server()
    s.register_tool("boom", lambda: (_ for _ in ()).throw(ValueError("bad")))
    with pytest.raises(Exception) as exc:
        s.execute("boom", {})
    assert "failed" in str(exc.value)
    assert s.execution_log[-1]["status"] == "error"


def test_rate_limit_rejection_is_logged_and_raises():
    s = make_server(rate_limit=2)
    s.register_tool("read", lambda path: f"c:{path}", cacheable=False)
    assert s.execute("read", {"path": "/1"}) == "c:/1"
    assert s.execute("read", {"path": "/2"}) == "c:/2"
    with pytest.raises(Exception) as exc:
        s.execute("read", {"path": "/3"})
    assert "Rate limit" in str(exc.value)
    # The rejection must be recorded in the execution log.
    statuses = [e["status"] for e in s.execution_log]
    assert "rate_limited" in statuses


def test_rate_limit_after_hook_fires_on_rejection():
    s = make_server(rate_limit=1)
    s.register_tool("read", lambda path: "c", cacheable=False)
    seen = []
    s.add_hook("after", lambda entry: seen.append(entry["status"]))
    s.execute("read", {"path": "/1"})
    with pytest.raises(Exception):
        s.execute("read", {"path": "/2"})
    assert "rate_limited" in seen


def test_stats_reporting():
    s = make_server()
    s.register_tool("read", lambda path: "c")
    s.register_tool("boom", lambda: (_ for _ in ()).throw(ValueError("x")))
    s.execute("read", {"path": "/1"})
    with pytest.raises(Exception):
        s.execute("boom", {})
    stats = s.get_stats()
    assert stats["total_executions"] == 2
    assert stats["successful"] == 1
    assert stats["failed"] == 1
    assert 0 <= stats["success_rate"] <= 1
    assert stats["tools"] == 2


def test_unserializable_params_cache_key_fallback():
    s = make_server()
    s.register_tool("t", lambda obj: "ok", cacheable=True)
    # set is not JSON-serializable; should not crash cache key generation
    assert s.execute("t", {"obj": {1, 2, 3}}) == "ok"

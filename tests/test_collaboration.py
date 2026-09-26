"""Tests for AgentCollaboration: negotiate, collaborate, vote."""
import pytest

from collaboration import AgentCollaboration
from multi_agent_system import MultiAgentSystem
from conftest import EchoAgent


def build():
    s = MultiAgentSystem()
    s.add_agent(EchoAgent("a1", "role", capabilities=["x"], priority=1))
    s.add_agent(EchoAgent("a2", "role", capabilities=["x"], priority=5))
    return AgentCollaboration(s), s


def test_negotiate_picks_highest_priority():
    collab, _ = build()
    assert collab.negotiate(["a1", "a2"], "task") == "a2"


def test_negotiate_no_valid_agents_raises():
    collab, _ = build()
    with pytest.raises(ValueError):
        collab.negotiate(["ghost"], "task")


def test_collaborate_runs_all_agents_in_order():
    collab, _ = build()
    result = collab.collaborate(["a1", "a2"], "team task")
    assert len(result["results"]) == 2
    assert result["agents"] == ["a1", "a2"]
    # second agent receives the first's result in context
    assert result["results"][0]["status"] == "completed"


def test_vote_returns_an_option():
    collab, _ = build()
    choice = collab.vote(["a1", "a2"], "pick", ["A", "B", "C"])
    assert choice in ["A", "B", "C"]


def test_vote_deterministic():
    collab, _ = build()
    c1 = collab.vote(["a1", "a2"], "pick", ["A", "B", "C"])
    c2 = collab.vote(["a1", "a2"], "pick", ["A", "B", "C"])
    assert c1 == c2  # hash-based, deterministic


def test_vote_empty_options_raises():
    collab, _ = build()
    with pytest.raises(ValueError):
        collab.vote(["a1"], "pick", [])


def test_vote_supports_unhashable_options():
    collab, _ = build()
    choice = collab.vote(["a1", "a2"], "pick", [{"k": 1}, {"k": 2}])
    assert choice in [{"k": 1}, {"k": 2}]

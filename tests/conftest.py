"""Shared pytest fixtures and helper agents for the multi-agent test suite."""
import os
import sys

import pytest

# Make the project root importable when tests run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent import Agent  # noqa: E402
from mcp_server import MCPServer  # noqa: E402
from multi_agent_system import MultiAgentSystem  # noqa: E402


class EchoAgent(Agent):
    """Agent whose _execute returns a deterministic value."""

    def _execute(self, task, context=None):
        return f"done:{task}"


class FailingAgent(Agent):
    """Agent that raises for the first N calls, then succeeds.

    Useful for exercising retry logic in Agent.process and Workflow.
    """

    def __init__(self, *args, fail_times=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_times = fail_times
        self.calls = 0

    def _execute(self, task, context=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"boom {self.calls}")
        return f"recovered after {self.calls}"


class AlwaysFailAgent(Agent):
    """Agent that always raises."""

    def _execute(self, task, context=None):
        raise RuntimeError("permanent failure")


@pytest.fixture
def echo_agent():
    return EchoAgent("echo", "echoes tasks", capabilities=["echo", "test"])


@pytest.fixture
def system(echo_agent):
    s = MultiAgentSystem(max_workers=4)
    s.add_agent(echo_agent)
    return s


@pytest.fixture
def mcp_server():
    server = MCPServer("test_server", "test", rate_limit=None)
    server.register_tool("read", lambda path: f"content:{path}", "read", cacheable=True)
    server.register_tool("boom", lambda: (_ for _ in ()).throw(ValueError("tool error")), "always errors")
    return server

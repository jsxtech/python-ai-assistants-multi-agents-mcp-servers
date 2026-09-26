"""Tests for resilience: CircuitBreaker, LoadBalancer, RateLimiter."""
import time

import pytest
from conftest import EchoAgent

from multi_agent_system import MultiAgentSystem
from resilience import CircuitBreaker, LoadBalancer, RateLimiter


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=2, timeout=60)

    def boom():
        raise RuntimeError("x")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(boom)
    assert cb.state == "open"
    # Further calls short-circuit
    with pytest.raises(Exception) as exc:
        cb.call(boom)
    assert "open" in str(exc.value)


def test_circuit_breaker_half_open_recovers():
    cb = CircuitBreaker(failure_threshold=1, timeout=0.05)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert cb.state == "open"
    time.sleep(0.06)
    # Successful call transitions half-open -> closed
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == "closed"
    assert cb.failures == 0


def build_system():
    s = MultiAgentSystem()
    s.add_agent(EchoAgent("a1", "role", capabilities=["cap"], priority=1))
    s.add_agent(EchoAgent("a2", "role", capabilities=["cap"], priority=2))
    return s


def test_load_balancer_round_robin():
    lb = LoadBalancer(build_system())
    lb.set_strategy("round_robin")
    picks = [lb.select_agent("cap") for _ in range(4)]
    # Alternates between the two agents
    assert picks[0] != picks[1]
    assert picks[0] == picks[2] and picks[1] == picks[3]


def test_load_balancer_least_busy():
    s = build_system()
    lb = LoadBalancer(s)
    lb.set_strategy("least_busy")
    s.delegate("a1", "t")  # a1 now busier
    assert lb.select_agent("cap") == "a2"


def test_load_balancer_no_agents_raises():
    lb = LoadBalancer(build_system())
    with pytest.raises(ValueError):
        lb.select_agent("missing")


def test_rate_limiter_allows_then_blocks():
    rl = RateLimiter(max_requests=2, window=60)
    assert rl.allow() is True
    assert rl.allow() is True
    assert rl.allow() is False
    assert rl.wait_time() > 0


def test_rate_limiter_window_reset():
    rl = RateLimiter(max_requests=1, window=0.05)
    assert rl.allow() is True
    assert rl.allow() is False
    time.sleep(0.06)
    assert rl.allow() is True

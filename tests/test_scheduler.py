"""Tests for TaskScheduler: delayed, recurring, cancellation, error isolation."""
import time

from scheduler import TaskScheduler
from multi_agent_system import MultiAgentSystem
from conftest import EchoAgent


def build_scheduler():
    s = MultiAgentSystem()
    s.add_agent(EchoAgent("a", "role"))
    return TaskScheduler(s), s


def test_delayed_task_runs_when_due():
    sched, _ = build_scheduler()
    sched.schedule("a", "t", delay=0)  # due immediately
    results = sched.run_pending()
    assert len(results) == 1
    assert results[0]["status"] == "completed"


def test_delayed_task_not_run_before_due():
    sched, _ = build_scheduler()
    sched.schedule("a", "t", delay=100)
    results = sched.run_pending()
    assert results == []


def test_completed_tasks_pruned():
    sched, _ = build_scheduler()
    sched.schedule("a", "t", delay=0)
    sched.run_pending()
    assert sched.get_scheduled_count()["pending"] == 0


def test_recurring_task_runs_and_reschedules():
    sched, _ = build_scheduler()
    sched.schedule_recurring("a", "t", interval=0)
    r1 = sched.run_pending()
    assert len(r1) == 1
    # next_run advanced but interval 0 -> due again
    r2 = sched.run_pending()
    assert len(r2) == 1


def test_cancel_recurring():
    sched, _ = build_scheduler()
    sched.schedule_recurring("a", "t", interval=0)
    sched.cancel_recurring(0)
    results = sched.run_pending()
    assert results == []
    assert sched.get_scheduled_count()["recurring_inactive"] == 1


def test_error_in_task_isolated():
    sched, s = build_scheduler()
    # Nonexistent agent -> delegate raises -> caught as error result
    sched.schedule("ghost", "t", delay=0)
    sched.schedule("a", "ok", delay=0)
    results = sched.run_pending()
    statuses = sorted(r["status"] for r in results)
    assert "completed" in statuses and "error" in statuses

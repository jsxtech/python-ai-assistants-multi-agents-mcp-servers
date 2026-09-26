"""Tests for EventBus: subscribe/publish, unsubscribe, history/filtering, handler isolation."""
import time

from event_bus import EventBus


def test_subscribe_and_publish():
    bus = EventBus()
    seen = []
    bus.subscribe("evt", lambda e: seen.append(e["data"]))
    bus.publish("evt", {"x": 1})
    assert seen == [{"x": 1}]


def test_unsubscribe():
    bus = EventBus()
    seen = []

    def handler(e):
        seen.append(e)

    bus.subscribe("evt", handler)
    bus.unsubscribe("evt", handler)
    bus.publish("evt", {"x": 1})
    assert seen == []


def test_unsubscribe_unknown_is_noop():
    bus = EventBus()
    bus.unsubscribe("evt", lambda e: None)  # should not raise


def test_bad_handler_isolated():
    bus = EventBus()
    seen = []
    bus.subscribe("evt", lambda e: (_ for _ in ()).throw(RuntimeError("bad")))
    bus.subscribe("evt", lambda e: seen.append("ok"))
    bus.publish("evt", {})
    assert seen == ["ok"]  # good handler still ran


def test_event_history_filtering_by_type():
    bus = EventBus()
    bus.publish("a", {})
    bus.publish("b", {})
    bus.publish("a", {})
    a_events = bus.get_events(event_type="a")
    assert len(a_events) == 2
    assert all(e["type"] == "a" for e in a_events)


def test_event_history_filtering_since():
    bus = EventBus()
    bus.publish("a", {})
    cutoff = time.time()
    time.sleep(0.01)
    bus.publish("a", {})
    recent = bus.get_events(since=cutoff)
    assert len(recent) == 1

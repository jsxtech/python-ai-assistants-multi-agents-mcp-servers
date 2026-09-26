"""Tests for AgentLearning: feedback, classification, export/import + validation."""
import json

import pytest
from conftest import EchoAgent

from learning import AgentLearning


def build():
    return AgentLearning(EchoAgent("a", "role"))


def test_learn_from_feedback_updates_patterns():
    lrn = build()
    lrn.learn_from_feedback("research AI trends", "good", 4.0)
    lrn.learn_from_feedback("find papers", "ok", 2.0)
    assert lrn.patterns["research"]["count"] == 2
    assert lrn.patterns["research"]["avg_rating"] == 3.0


def test_classify_task_categories():
    lrn = build()
    assert lrn._classify_task("write code") == "coding"
    assert lrn._classify_task("analyze data") == "analysis"
    assert lrn._classify_task("research topic") == "research"
    assert lrn._classify_task("something else") == "general"


def test_best_task_types_sorted():
    lrn = build()
    lrn.learn_from_feedback("write code", "great", 5.0)
    lrn.learn_from_feedback("research x", "meh", 1.0)
    best = lrn.get_best_task_types()
    assert best[0][0] == "coding"


def test_export_import_roundtrip():
    lrn = build()
    lrn.learn_from_feedback("write code", "great", 5.0)
    exported = lrn.export_knowledge()
    other = build()
    other.import_knowledge(exported)
    assert other.patterns["coding"]["avg_rating"] == 5.0


def test_import_invalid_json_raises():
    lrn = build()
    with pytest.raises(ValueError):
        lrn.import_knowledge("{not valid json")


def test_import_non_dict_raises():
    lrn = build()
    with pytest.raises(ValueError):
        lrn.import_knowledge(json.dumps([1, 2, 3]))


def test_import_bad_pattern_shape_raises():
    lrn = build()
    with pytest.raises(ValueError):
        lrn.import_knowledge(json.dumps({"coding": {"count": "not a number", "avg_rating": 1}}))


def test_import_pattern_not_object_raises():
    lrn = build()
    with pytest.raises(ValueError):
        lrn.import_knowledge(json.dumps({"coding": "nope"}))

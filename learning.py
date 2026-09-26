import json
from collections import deque
from typing import Dict, List


class AgentLearning:
    MAX_FEEDBACK_HISTORY = 1000

    def __init__(self, agent):
        self.agent = agent
        self.patterns: Dict[str, Dict] = {}
        self.feedback_history = deque(maxlen=self.MAX_FEEDBACK_HISTORY)

    def learn_from_feedback(self, task: str, feedback: str, rating: float):
        """Learn from task feedback"""
        self.feedback_history.append({
            "task": task,
            "feedback": feedback,
            "rating": rating
        })

        # Update patterns
        task_type = self._classify_task(task)
        if task_type not in self.patterns:
            self.patterns[task_type] = {"count": 0, "avg_rating": 0}

        pattern = self.patterns[task_type]
        pattern["count"] += 1
        pattern["avg_rating"] = (pattern["avg_rating"] * (pattern["count"] - 1) + rating) / pattern["count"]

    def _classify_task(self, task: str) -> str:
        """Simple task classification"""
        keywords = {
            "research": ["research", "find", "search", "investigate"],
            "coding": ["write", "code", "implement", "develop"],
            "analysis": ["analyze", "process", "evaluate", "assess"]
        }

        task_lower = task.lower()
        for category, words in keywords.items():
            if any(word in task_lower for word in words):
                return category
        return "general"

    def get_best_task_types(self) -> List:
        """Get task types agent performs best at"""
        return sorted(self.patterns.items(), key=lambda x: x[1]["avg_rating"], reverse=True)

    def export_knowledge(self) -> str:
        """Export learned patterns"""
        return json.dumps(self.patterns, indent=2)

    def import_knowledge(self, knowledge: str):
        """Import learned patterns.

        Validates that the payload is a JSON object mapping task types to
        pattern dicts with numeric ``count`` and ``avg_rating`` fields. Raises
        ValueError on malformed input rather than silently corrupting state.
        """
        try:
            data = json.loads(knowledge)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid knowledge JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Knowledge must be a JSON object of task-type patterns")

        validated: Dict[str, Dict] = {}
        for task_type, pattern in data.items():
            if not isinstance(pattern, dict):
                raise ValueError(f"Pattern for '{task_type}' must be an object")
            count = pattern.get("count", 0)
            avg_rating = pattern.get("avg_rating", 0)
            if not isinstance(count, (int, float)) or not isinstance(avg_rating, (int, float)):
                raise ValueError(f"Pattern for '{task_type}' must have numeric count and avg_rating")
            validated[str(task_type)] = {"count": count, "avg_rating": avg_rating}

        self.patterns = validated

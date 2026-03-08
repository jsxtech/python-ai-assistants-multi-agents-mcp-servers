from typing import Dict, List
import json

class AgentLearning:
    def __init__(self, agent):
        self.agent = agent
        self.patterns = {}
        self.feedback_history = []
    
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
    
    def get_best_task_types(self) -> List[str]:
        """Get task types agent performs best at"""
        return sorted(self.patterns.items(), key=lambda x: x[1]["avg_rating"], reverse=True)
    
    def export_knowledge(self) -> str:
        """Export learned patterns"""
        return json.dumps(self.patterns, indent=2)
    
    def import_knowledge(self, knowledge: str):
        """Import learned patterns"""
        self.patterns = json.loads(knowledge)

import json
import time
from typing import Dict, Any

class StateManager:
    def __init__(self, filepath: str = "system_state.json"):
        self.filepath = filepath
        self.state = {}
    
    def save_state(self, system):
        """Save system state to file"""
        state = {
            "agents": {
                name: {
                    "role": agent.role,
                    "capabilities": agent.capabilities,
                    "memory": [
                        {k: v for k, v in m.items() if k != "value" or not callable(v)}
                        for m in agent.memory[-10:]
                    ],
                    "task_count": len(agent.task_history)
                }
                for name, agent in system.agents.items()
            },
            "shared_memory_keys": list(system.shared_memory.keys()),
            "timestamp": time.time()
        }
        
        with open(self.filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self) -> Dict:
        """Load system state from file"""
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def checkpoint(self, system, name: str):
        """Create named checkpoint"""
        checkpoint_file = f"{self.filepath}.{name}"
        original_filepath = self.filepath
        self.filepath = checkpoint_file
        self.save_state(system)
        self.filepath = original_filepath
    
    def restore_checkpoint(self, name: str) -> Dict:
        """Restore from named checkpoint"""
        checkpoint_file = f"{self.filepath}.{name}"
        original_filepath = self.filepath
        self.filepath = checkpoint_file
        state = self.load_state()
        self.filepath = original_filepath
        return state

class MetricsCollector:
    def __init__(self):
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0,
            "agent_metrics": {}
        }
    
    def record(self, agent_name: str, result: Dict):
        """Record task execution metrics"""
        self.metrics["requests"] += 1
        
        if result["status"] == "completed":
            self.metrics["successes"] += 1
        else:
            self.metrics["failures"] += 1
        
        self.metrics["total_duration"] += result.get("duration", 0)
        
        if agent_name not in self.metrics["agent_metrics"]:
            self.metrics["agent_metrics"][agent_name] = {
                "requests": 0,
                "successes": 0,
                "failures": 0
            }
        
        agent_metrics = self.metrics["agent_metrics"][agent_name]
        agent_metrics["requests"] += 1
        if result["status"] == "completed":
            agent_metrics["successes"] += 1
        else:
            agent_metrics["failures"] += 1
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        total = self.metrics["requests"]
        return {
            "total_requests": total,
            "success_rate": self.metrics["successes"] / total if total > 0 else 0,
            "avg_duration": self.metrics["total_duration"] / total if total > 0 else 0,
            "agent_metrics": self.metrics["agent_metrics"]
        }
    
    def reset(self):
        """Reset all metrics"""
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0,
            "agent_metrics": {}
        }

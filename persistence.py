import json
import time
from typing import Dict, Any


class StateManager:
    def __init__(self, filepath: str = "system_state.json"):
        self.filepath = filepath

    def save_state(self, system, filepath: str = None):
        """Save system state to file"""
        filepath = filepath or self.filepath

        # Acquire system lock to get a consistent snapshot of agents
        with system._lock:
            agents_snapshot = dict(system.agents)
            shared_keys = list(system.shared_memory.keys())

        # Snapshot each agent's memory under its own lock. recall()/remember()
        # mutate the dict from other threads, so iterating it directly here could
        # raise "dictionary changed size during iteration".
        agent_memory_snapshots = {}
        for name, agent in agents_snapshot.items():
            lock = getattr(agent, "_lock", None)
            if lock is not None:
                with lock:
                    agent_memory_snapshots[name] = list(agent.memory.items())[:50]
            else:
                agent_memory_snapshots[name] = list(agent.memory.items())[:50]

        state = {
            "agents": {
                name: {
                    "role": agent.role,
                    "capabilities": agent.capabilities,
                    "memory": {
                        k: {mk: mv for mk, mv in m.items() if not callable(mv)}
                        for k, m in agent_memory_snapshots[name]
                    },
                    "task_count": len(agent.task_history)
                }
                for name, agent in agents_snapshot.items()
            },
            "shared_memory_keys": shared_keys,
            "timestamp": time.time()
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self, filepath: str = None) -> Dict:
        """Load system state from file"""
        filepath = filepath or self.filepath
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def checkpoint(self, system, name: str):
        """Create named checkpoint"""
        checkpoint_file = f"{self.filepath}.{name}"
        self.save_state(system, filepath=checkpoint_file)

    def restore_checkpoint(self, name: str) -> Dict:
        """Restore from named checkpoint"""
        checkpoint_file = f"{self.filepath}.{name}"
        return self.load_state(filepath=checkpoint_file)


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

        is_success = result.get("status") == "completed"
        if is_success:
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
        if is_success:
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

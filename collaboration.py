from typing import Dict, List, Any
from collections import deque
import time
import hashlib


class AgentCollaboration:
    MAX_HISTORY = 500

    def __init__(self, system):
        self.system = system
        self.collaboration_history: deque = deque(maxlen=self.MAX_HISTORY)

    def negotiate(self, agents: List[str], task: str) -> str:
        """Select best agent through negotiation based on metrics.

        Uses the system's lock-protected agent access to avoid race conditions.
        """
        with self.system._lock:
            candidates = [self.system.agents[name] for name in agents if name in self.system.agents]
        if not candidates:
            raise ValueError("No valid agents for negotiation")

        best = max(candidates, key=lambda a: (
            a.priority,
            a.get_metrics()["success_rate"],
            -len(a.task_history)
        ))
        return best.name

    def collaborate(self, agents: List[str], task: str) -> Dict:
        """Multiple agents work together on a task"""
        start_time = time.time()
        results = []

        for agent_name in agents:
            context = {"previous_results": results[:]}  # Pass a copy to avoid mutation
            result = self.system.delegate(agent_name, task, context)
            results.append(result)

        collaboration = {
            "agents": agents,
            "task": task,
            "results": results,
            "duration": time.time() - start_time
        }
        self.collaboration_history.append(collaboration)
        return collaboration

    def vote(self, agents: List[str], task: str, options: List[Any]) -> Any:
        """Agents vote on best option.

        Each agent's vote is determined by delegating the task and using the
        agent's name + task hash to pick from the available options. This
        produces a deterministic but varied distribution of votes across agents.

        Supports unhashable option types (dicts, lists, etc.) by using index-based counting.
        """
        if not options:
            raise ValueError("Options list cannot be empty")

        # Use index-based vote counting to support unhashable options
        vote_counts: List[int] = [0] * len(options)

        for agent_name in agents:
            # Delegate to get the agent involved (side-effect: recorded in history)
            self.system.delegate(agent_name, f"Vote on: {task} — options: {options}")

            # Deterministic vote based on agent name + task (simulates preference)
            hash_input = f"{agent_name}:{task}"
            idx = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16) % len(options)
            vote_counts[idx] += 1

        # Return the option with the most votes (first one wins ties)
        best_idx = max(range(len(options)), key=lambda i: vote_counts[i])
        return options[best_idx]

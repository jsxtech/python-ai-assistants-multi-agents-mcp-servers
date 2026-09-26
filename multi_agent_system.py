from typing import List, Dict, Any, Callable, Optional
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent import Agent
import time
import threading


class MultiAgentSystem:
    MAX_EVENT_LOG = 2000

    def __init__(self, max_workers: int = 10):
        self.agents: Dict[str, Agent] = {}
        self.shared_memory: Dict[str, Dict] = {}
        self.event_log = deque(maxlen=self.MAX_EVENT_LOG)
        self.max_workers = max_workers
        self.middleware: List[Callable] = []
        self._lock = threading.Lock()

    def add_agent(self, agent: Agent):
        with self._lock:
            self.agents[agent.name] = agent
        self.log_event("agent_added", {"agent": agent.name, "role": agent.role})

    def remove_agent(self, agent_name: str):
        with self._lock:
            if agent_name in self.agents:
                del self.agents[agent_name]
        self.log_event("agent_removed", {"agent": agent_name})

    def add_middleware(self, middleware: Callable):
        self.middleware.append(middleware)

    def delegate(self, agent_name: str, task: str, context: Optional[Dict] = None, priority: int = 0) -> Dict:
        with self._lock:
            agent = self.agents.get(agent_name)
        if agent is None:
            raise ValueError(f"Agent {agent_name} not found")

        # Apply middleware
        for mw in self.middleware:
            task, context = mw(agent_name, task, context)

        return agent.process(task, context)

    def parallel_execute(self, tasks: List[Dict[str, str]], timeout: Optional[int] = None) -> List[Dict]:
        """Execute tasks in parallel, returning results in the same order as the input tasks list.

        If timeout is exceeded, tasks that haven't completed will have status 'error' with a timeout message.
        """
        if not tasks:
            return []

        results: List[Dict] = [{"status": "error", "error": "Task did not complete"} for _ in range(len(tasks))]

        with ThreadPoolExecutor(max_workers=min(len(tasks), self.max_workers)) as executor:
            future_to_index = {}
            for i, task in enumerate(tasks):
                future = executor.submit(
                    self.delegate,
                    task["agent"],
                    task["task"],
                    task.get("context"),
                    task.get("priority", 0)
                )
                future_to_index[future] = i

            try:
                for future in as_completed(future_to_index, timeout=timeout):
                    idx = future_to_index[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        results[idx] = {"status": "error", "error": str(e)}
            except TimeoutError:
                # Some futures didn't complete within the timeout.
                # Mark incomplete ones with a timeout error (they already have the default).
                for future, idx in future_to_index.items():
                    if not future.done():
                        results[idx] = {"status": "error", "error": "Task timed out"}
                        future.cancel()

        return results

    def broadcast(self, task: str) -> List[Dict]:
        with self._lock:
            agents = list(self.agents.values())
        return [agent.process(task) for agent in agents]

    def find_agent_by_capability(self, capability: str) -> List[Agent]:
        with self._lock:
            return [agent for agent in self.agents.values() if capability in agent.capabilities]

    def get_best_agent(self, capability: str) -> Agent:
        candidates = self.find_agent_by_capability(capability)
        if not candidates:
            raise ValueError(f"No agent with capability '{capability}'")
        return max(candidates, key=lambda a: (a.priority, a.get_metrics()["success_rate"]))

    def auto_delegate(self, task: str, capability: str, context: Optional[Dict] = None) -> Dict:
        agent = self.get_best_agent(capability)
        return self.delegate(agent.name, task, context)

    def share_data(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            self.shared_memory[key] = {
                "value": value,
                "timestamp": time.time(),
                "expires_at": time.time() + ttl if ttl is not None else None
            }

    def get_shared_data(self, key: str) -> Any:
        with self._lock:
            data = self.shared_memory.get(key)
            if data:
                if data["expires_at"] is None or data["expires_at"] > time.time():
                    return data["value"]
                else:
                    # Expired — clean up
                    del self.shared_memory[key]
        return None

    def log_event(self, event_type: str, data: Dict):
        self.event_log.append({"type": event_type, "data": data, "timestamp": time.time()})

    def get_system_status(self) -> Dict:
        with self._lock:
            agents_snapshot = dict(self.agents)
            shared_memory_keys = list(self.shared_memory.keys())
            total_events = len(self.event_log)
        # Agent state/metrics are read outside the system lock; each agent guards
        # its own internal state, and this avoids holding the system lock during
        # potentially slow metric computation.
        agents_status = {name: {
            "role": agent.role,
            "state": agent.state,
            "tasks_completed": len(agent.task_history),
            "metrics": agent.get_metrics()
        } for name, agent in agents_snapshot.items()}
        return {
            "agents": agents_status,
            "shared_memory_keys": shared_memory_keys,
            "total_events": total_events,
            "active_agents": sum(1 for a in agents_snapshot.values() if a.state == "busy")
        }

    def get_agent_leaderboard(self) -> List[Dict]:
        with self._lock:
            agents_snapshot = dict(self.agents)
        return sorted([
            {"name": name, "metrics": agent.get_metrics()}
            for name, agent in agents_snapshot.items()
        ], key=lambda x: x["metrics"]["success_rate"], reverse=True)

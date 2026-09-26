from typing import List, Dict, Any, Callable, Optional
from collections import deque
import time
import threading


class Agent:
    MAX_HISTORY = 1000
    MAX_CONTEXT = 200

    def __init__(self, name: str, role: str, mcp_servers: Optional[List] = None, capabilities: Optional[List[str]] = None, priority: int = 0):
        self.name = name
        self.role = role
        self.mcp_servers = mcp_servers or []
        self.capabilities = capabilities or []
        self.priority = priority
        self.context: deque = deque(maxlen=self.MAX_CONTEXT)
        self.memory: Dict[str, Dict] = {}
        self.task_history: deque = deque(maxlen=self.MAX_HISTORY)
        self.callbacks: List[Callable] = []
        self.state = "idle"
        self.max_retries = 3
        self._lock = threading.Lock()

    def add_mcp_server(self, server):
        self.mcp_servers.append(server)

    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)

    def use_tool(self, server_name: str, tool_name: str, params: dict) -> Any:
        for server in self.mcp_servers:
            if server.name == server_name:
                return server.execute(tool_name, params)
        raise ValueError(f"Server {server_name} not found")

    def remember(self, key: str, value: Any, ttl: int = None):
        self.memory[key] = {
            "key": key,
            "value": value,
            "timestamp": time.time(),
            "expires_at": time.time() + ttl if ttl is not None else None
        }

    def recall(self, key: str) -> Any:
        item = self.memory.get(key)
        if item is None:
            return None
        if item["expires_at"] is None or item["expires_at"] > time.time():
            return item["value"]
        # Expired — clean up
        del self.memory[key]
        return None

    def forget(self, key: str):
        self.memory.pop(key, None)

    def clear_memory(self):
        self.memory.clear()

    def _execute(self, task: str, context: Optional[Dict] = None) -> Any:
        """Override this method in subclasses to perform actual work (e.g. call an LLM).

        Returns any result payload, or raises an exception on failure.
        By default, returns None (the base agent just records the task).
        """
        return None

    def process(self, task: str, context: Optional[Dict] = None, retry: int = 0) -> Dict[str, Any]:
        with self._lock:
            self.state = "busy"

        start_time = time.time()
        self.context.append({"role": "user", "content": task})

        # Clamp retry to valid range
        retry = min(retry, self.max_retries)
        result = None

        for attempt in range(retry, self.max_retries + 1):
            try:
                work_result = self._execute(task, context)
                result = {
                    "agent": self.name,
                    "task": task,
                    "status": "completed",
                    "result": work_result,
                    "duration": time.time() - start_time,
                    "context": context,
                    "retry_count": attempt
                }
                break
            except Exception as e:
                if attempt >= self.max_retries:
                    result = {
                        "agent": self.name,
                        "task": task,
                        "status": "failed",
                        "error": str(e),
                        "duration": time.time() - start_time,
                        "retry_count": attempt
                    }

        # Defensive fallback: the loop above always assigns `result`, but guard
        # against future changes leaving it None so we never corrupt task_history.
        if result is None:
            result = {
                "agent": self.name,
                "task": task,
                "status": "failed",
                "error": "No result produced",
                "duration": time.time() - start_time,
                "retry_count": self.max_retries
            }

        self.task_history.append(result)

        with self._lock:
            self.state = "idle"

        for callback in self.callbacks:
            try:
                callback(result)
            except Exception:
                pass  # Don't let a bad callback affect the caller

        return result

    def get_available_tools(self) -> Dict[str, List[str]]:
        return {server.name: server.list_tools() for server in self.mcp_servers}

    def get_metrics(self) -> Dict:
        total = len(self.task_history)
        completed = sum(1 for t in self.task_history if t["status"] == "completed")
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": total - completed,
            "success_rate": completed / total if total > 0 else 0,
            "avg_duration": sum(t["duration"] for t in self.task_history) / total if total > 0 else 0
        }

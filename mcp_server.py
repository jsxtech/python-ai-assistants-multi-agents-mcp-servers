import json
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class MCPServer:
    MAX_LOG_SIZE = 2000

    def __init__(self, name: str, description: str = "", rate_limit: Optional[int] = None):
        self.name = name
        self.description = description
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict] = {}
        self.execution_log = deque(maxlen=self.MAX_LOG_SIZE)
        self.rate_limit = rate_limit
        self.rate_limit_window: list = []
        self.cache: Dict[str, Dict] = {}
        self.hooks: Dict[str, list] = {"before": [], "after": []}
        self._rate_limit_lock = threading.Lock()
        self._state_lock = threading.Lock()  # guards execution_log and cache

    def register_tool(self, name: str, func: Callable, description: str = "", params_schema: Optional[Dict] = None, cacheable: bool = False):
        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered on server '{self.name}' — overwriting")
        self.tools[name] = func
        self.tool_metadata[name] = {
            "description": description,
            "params_schema": params_schema or {},
            "cacheable": cacheable
        }

    def add_hook(self, hook_type: str, func: Callable):
        if hook_type in self.hooks:
            self.hooks[hook_type].append(func)

    def _check_rate_limit(self):
        if self.rate_limit:
            with self._rate_limit_lock:
                current_time = time.time()
                self.rate_limit_window = [t for t in self.rate_limit_window if current_time - t < 60]
                if len(self.rate_limit_window) >= self.rate_limit:
                    return False
                self.rate_limit_window.append(current_time)
        return True

    def _get_cache_key(self, tool_name: str, params: dict) -> str:
        try:
            params_str = json.dumps(params, sort_keys=True)
        except (TypeError, ValueError):
            # Params contain non-serializable values — fall back to repr
            params_str = repr(sorted(params.items()))
        return f"{tool_name}:{params_str}"

    def execute(self, tool_name: str, params: dict, use_cache: bool = True) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        if not self._check_rate_limit():
            # Record the rejection so it surfaces in stats/observability.
            log_entry = {
                "tool": tool_name,
                "params": params,
                "result": "Rate limit exceeded",
                "status": "rate_limited",
                "duration": 0.0,
                "timestamp": time.time()
            }
            with self._state_lock:
                self.execution_log.append(log_entry)
            for hook in self.hooks["after"]:
                hook(log_entry)
            raise Exception(f"Rate limit exceeded for server '{self.name}'")

        # Check cache (defensive .get avoids a check-then-act race with clear_cache)
        cache_key = self._get_cache_key(tool_name, params)
        if use_cache and self.tool_metadata[tool_name].get("cacheable"):
            with self._state_lock:
                cached = self.cache.get(cache_key)
            if cached is not None:
                return cached["result"]

        # Before hooks
        for hook in self.hooks["before"]:
            hook(tool_name, params)

        start_time = time.time()
        error = None
        try:
            result = self.tools[tool_name](**params)
            status = "success"

            # Cache result
            if self.tool_metadata[tool_name].get("cacheable"):
                with self._state_lock:
                    self.cache[cache_key] = {"result": result, "timestamp": time.time()}
        except Exception as e:
            result = str(e)
            status = "error"
            error = e

        log_entry = {
            "tool": tool_name,
            "params": params,
            "result": result,
            "status": status,
            "duration": time.time() - start_time,
            "timestamp": time.time()
        }

        with self._state_lock:
            self.execution_log.append(log_entry)

        # After hooks
        for hook in self.hooks["after"]:
            hook(log_entry)

        if status == "error":
            raise Exception(f"Tool '{tool_name}' failed: {result}") from error

        return result

    def clear_cache(self):
        with self._state_lock:
            self.cache.clear()

    def list_tools(self) -> list:
        return list(self.tools.keys())

    def get_tool_info(self, tool_name: str) -> Dict:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self.tool_metadata.get(tool_name, {})

    def get_stats(self) -> Dict:
        # Snapshot under lock: execute() appends to execution_log from worker
        # threads, and a bounded deque at maxlen evicts mid-iteration, which
        # would otherwise raise RuntimeError: deque mutated during iteration.
        with self._state_lock:
            logs = list(self.execution_log)
            cache_size = len(self.cache)
        total = len(logs)
        success = sum(1 for log in logs if log["status"] == "success")
        avg_duration = sum(log["duration"] for log in logs) / total if total > 0 else 0
        return {
            "server": self.name,
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration": avg_duration,
            "tools": len(self.tools),
            "cache_size": cache_size
        }

from typing import List
import time
import threading


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: float = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self._lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self.state == "half-open":
                    self.state = "closed"
                    self.failures = 0
            return result
        except Exception:
            with self._lock:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    self.state = "open"
            raise


class LoadBalancer:
    def __init__(self, system):
        self.system = system
        self.strategy = "round_robin"
        self.current_index = 0
        self._lock = threading.Lock()

    def set_strategy(self, strategy: str):
        """Set load balancing strategy: round_robin, least_busy, best_performance"""
        self.strategy = strategy

    def select_agent(self, capability: str) -> str:
        agents = self.system.find_agent_by_capability(capability)
        if not agents:
            raise ValueError(f"No agents with capability '{capability}'")

        if self.strategy == "round_robin":
            with self._lock:
                agent = agents[self.current_index % len(agents)]
                self.current_index += 1
            return agent.name

        elif self.strategy == "least_busy":
            return min(agents, key=lambda a: len(a.task_history)).name

        elif self.strategy == "best_performance":
            return max(agents, key=lambda a: a.get_metrics()["success_rate"]).name

        return agents[0].name


class RateLimiter:
    def __init__(self, max_requests: int, window: float = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: List[float] = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        current_time = time.time()
        with self._lock:
            self.requests = [t for t in self.requests if current_time - t < self.window]
            if len(self.requests) < self.max_requests:
                self.requests.append(current_time)
                return True
        return False

    def wait_time(self) -> float:
        with self._lock:
            if not self.requests:
                return 0
            return max(0, self.window - (time.time() - self.requests[0]))

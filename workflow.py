from typing import List, Dict, Callable, Optional
from collections import deque
from multi_agent_system import MultiAgentSystem
import time


class Workflow:
    MAX_HISTORY = 500

    def __init__(self, name: str, max_retries: int = 3):
        self.name = name
        self.steps: List[Dict] = []
        self.max_retries = max_retries
        self.execution_history: deque = deque(maxlen=self.MAX_HISTORY)
        self.error_handlers: Dict[int, Callable] = {}

    def add_step(self, agent_name: str, task: str, depends_on: Optional[List[int]] = None, condition: Optional[Callable] = None):
        step_id = len(self.steps)
        # Validate dependency indices
        if depends_on:
            for dep in depends_on:
                if dep < 0 or dep >= step_id:
                    raise ValueError(f"Invalid dependency {dep} for step {step_id}")
        self.steps.append({
            "agent": agent_name,
            "task": task,
            "depends_on": depends_on or [],
            "condition": condition,
            "step_id": step_id
        })

    def add_error_handler(self, step_id: int, handler: Callable):
        self.error_handlers[step_id] = handler

    def execute(self, system: MultiAgentSystem, parallel: bool = False) -> List[Dict]:
        start_time = time.time()

        if parallel:
            results = self._execute_parallel(system)
        else:
            results = self._execute_sequential(system)

        execution_record = {
            "workflow": self.name,
            "duration": time.time() - start_time,
            "steps_completed": len(results),
            "timestamp": time.time()
        }
        self.execution_history.append(execution_record)

        return results

    def _execute_sequential(self, system: MultiAgentSystem) -> List[Dict]:
        results = {}
        skipped: set = set()

        for step in self.steps:
            # Skip if any dependency was skipped (cascade skip)
            if any(dep_id in skipped for dep_id in step["depends_on"]):
                skipped.add(step["step_id"])
                continue

            # Check condition
            if step["condition"] and not step["condition"](results):
                skipped.add(step["step_id"])
                continue

            # Verify dependencies completed
            for dep_id in step["depends_on"]:
                if dep_id not in results:
                    raise ValueError(f"Dependency {dep_id} not completed for step {step['step_id']}")

            # Execute step with retry
            context = {f"step_{dep_id}": results[dep_id] for dep_id in step["depends_on"]}

            last_result = None
            for attempt in range(self.max_retries):
                try:
                    result = system.delegate(step["agent"], step["task"], context)
                    last_result = result

                    # The agent catches its own exceptions and reports failure via
                    # status rather than raising, so retry here on reported failure.
                    if result.get("status") == "failed":
                        if attempt < self.max_retries - 1:
                            continue  # retry
                        # Retries exhausted — route to error handler if present
                        if step["step_id"] in self.error_handlers:
                            error = Exception(result.get("error", "Agent task failed"))
                            result = self.error_handlers[step["step_id"]](error, step, context)
                        results[step["step_id"]] = result
                        break

                    results[step["step_id"]] = result
                    break
                except Exception as e:
                    if step["step_id"] in self.error_handlers:
                        result = self.error_handlers[step["step_id"]](e, step, context)
                        results[step["step_id"]] = result
                        break
                    if attempt == self.max_retries - 1:
                        raise
            else:
                # Loop finished without break (all retries returned failure and no
                # handler consumed it) — persist the last observed result.
                if last_result is not None:
                    results[step["step_id"]] = last_result

        return list(results.values())

    def _execute_parallel(self, system: MultiAgentSystem) -> List[Dict]:
        # Compute dependency level for each step
        step_levels: Dict[int, int] = {}
        for step in self.steps:
            if not step["depends_on"]:
                step_levels[step["step_id"]] = 0
            else:
                step_levels[step["step_id"]] = max(step_levels[dep] for dep in step["depends_on"]) + 1

        # Group steps by level
        level_steps: Dict[int, List[Dict]] = {}
        for step in self.steps:
            level = step_levels[step["step_id"]]
            if level not in level_steps:
                level_steps[level] = []
            level_steps[level].append(step)

        results: Dict[int, Dict] = {}
        skipped: set = set()

        for level in sorted(level_steps.keys()):
            # Filter steps: skip if any dependency was skipped or condition fails
            eligible_steps = []
            for step in level_steps[level]:
                # Cascade skip: if any dependency was skipped, skip this step too
                if any(dep_id in skipped for dep_id in step["depends_on"]):
                    skipped.add(step["step_id"])
                    continue
                # Condition check
                if step["condition"] and not step["condition"](results):
                    skipped.add(step["step_id"])
                    continue
                eligible_steps.append(step)

            if not eligible_steps:
                continue

            tasks = []
            for step in eligible_steps:
                context = {f"step_{dep_id}": results[dep_id] for dep_id in step["depends_on"] if dep_id in results}
                tasks.append({
                    "agent": step["agent"],
                    "task": step["task"],
                    "context": context
                })

            level_results = system.parallel_execute(tasks)

            for i, step in enumerate(eligible_steps):
                step_result = level_results[i]
                step_context = {f"step_{dep_id}": results[dep_id] for dep_id in step["depends_on"] if dep_id in results}

                # Retry failed/errored steps (agents report failure via status
                # rather than raising, so parallel_execute returns a result dict).
                attempt = 1
                while step_result.get("status") in ("error", "failed") and attempt < self.max_retries:
                    retry_results = system.parallel_execute([{
                        "agent": step["agent"],
                        "task": step["task"],
                        "context": step_context
                    }])
                    step_result = retry_results[0]
                    attempt += 1

                # Still failing after retries — route to error handler if present
                if step_result.get("status") in ("error", "failed") and step["step_id"] in self.error_handlers:
                    error = Exception(step_result.get("error", "Task failed"))
                    step_result = self.error_handlers[step["step_id"]](error, step, step_context)
                results[step["step_id"]] = step_result

        return list(results.values())

    def get_stats(self) -> Dict:
        if not self.execution_history:
            return {"executions": 0}

        total = len(self.execution_history)
        avg_duration = sum(e["duration"] for e in self.execution_history) / total
        avg_steps = sum(e["steps_completed"] for e in self.execution_history) / total
        return {
            "workflow": self.name,
            "executions": total,
            "avg_duration": avg_duration,
            "avg_steps_completed": avg_steps,
            "total_steps": len(self.steps)
        }

from typing import List, Dict, Any, Callable
from agent import Agent
from multi_agent_system import MultiAgentSystem
import time

class Workflow:
    def __init__(self, name: str, max_retries: int = 3):
        self.name = name
        self.steps = []
        self.max_retries = max_retries
        self.execution_history = []
        self.error_handlers = {}
    
    def add_step(self, agent_name: str, task: str, depends_on: List[int] = None, condition: Callable = None):
        self.steps.append({
            "agent": agent_name,
            "task": task,
            "depends_on": depends_on or [],
            "condition": condition,
            "step_id": len(self.steps)
        })
    
    def add_error_handler(self, step_id: int, handler: Callable):
        self.error_handlers[step_id] = handler
    
    def execute(self, system: MultiAgentSystem, parallel: bool = False) -> List[Dict]:
        start_time = time.time()
        results = {}
        
        if parallel:
            return self._execute_parallel(system)
        
        for step in self.steps:
            # Check condition
            if step["condition"] and not step["condition"](results):
                continue
            
            # Wait for dependencies
            for dep_id in step["depends_on"]:
                if dep_id not in results:
                    raise ValueError(f"Dependency {dep_id} not completed")
            
            # Execute step with retry
            context = {f"step_{dep_id}": results[dep_id] for dep_id in step["depends_on"]}
            
            for attempt in range(self.max_retries):
                try:
                    result = system.delegate(step["agent"], step["task"], context)
                    results[step["step_id"]] = result
                    break
                except Exception as e:
                    if step["step_id"] in self.error_handlers:
                        result = self.error_handlers[step["step_id"]](e, step, context)
                        results[step["step_id"]] = result
                        break
                    if attempt == self.max_retries - 1:
                        raise
        
        execution_record = {
            "workflow": self.name,
            "duration": time.time() - start_time,
            "steps_completed": len(results),
            "timestamp": time.time()
        }
        self.execution_history.append(execution_record)
        
        return list(results.values())
    
    def _execute_parallel(self, system: MultiAgentSystem) -> List[Dict]:
        # Group steps by dependency level
        levels = {}
        for step in self.steps:
            level = max([levels.get(dep, 0) for dep in step["depends_on"]], default=0) + 1
            if level not in levels:
                levels[level] = []
            levels[level].append(step)
        
        results = {}
        for level in sorted(levels.keys()):
            tasks = []
            for step in levels[level]:
                context = {f"step_{dep_id}": results[dep_id] for dep_id in step["depends_on"]}
                tasks.append({
                    "agent": step["agent"],
                    "task": step["task"],
                    "context": context
                })
            
            level_results = system.parallel_execute(tasks)
            for i, step in enumerate(levels[level]):
                results[step["step_id"]] = level_results[i]
        
        return list(results.values())
    
    def get_stats(self) -> Dict:
        if not self.execution_history:
            return {"executions": 0}
        
        total = len(self.execution_history)
        avg_duration = sum(e["duration"] for e in self.execution_history) / total
        return {
            "workflow": self.name,
            "executions": total,
            "avg_duration": avg_duration,
            "total_steps": len(self.steps)
        }

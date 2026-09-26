from typing import Dict, List, Optional
import time


class TaskScheduler:
    def __init__(self, system):
        self.system = system
        self.scheduled_tasks: List[Dict] = []
        self.recurring_tasks: List[Dict] = []

    def schedule(self, agent_name: str, task: str, delay: float, context: Optional[Dict] = None):
        """Schedule task to run after delay (seconds)"""
        self.scheduled_tasks.append({
            "agent": agent_name,
            "task": task,
            "context": context,
            "execute_at": time.time() + delay,
            "status": "pending"
        })

    def schedule_recurring(self, agent_name: str, task: str, interval: float, context: Optional[Dict] = None):
        """Schedule recurring task"""
        self.recurring_tasks.append({
            "agent": agent_name,
            "task": task,
            "context": context,
            "interval": interval,
            "next_run": time.time() + interval,
            "active": True
        })

    def run_pending(self) -> List[Dict]:
        """Execute all pending scheduled tasks.

        Exceptions from individual tasks are caught and recorded as error results,
        allowing other pending tasks to still execute.
        """
        current_time = time.time()
        results = []

        # Run scheduled tasks
        pending = [t for t in self.scheduled_tasks if t["status"] == "pending" and t["execute_at"] <= current_time]
        for task in pending:
            try:
                result = self.system.delegate(task["agent"], task["task"], task["context"])
            except Exception as e:
                result = {"agent": task["agent"], "task": task["task"], "status": "error", "error": str(e)}
            task["status"] = "completed"
            results.append(result)

        # Prune completed one-shot tasks to prevent unbounded growth
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t["status"] == "pending"]

        # Run recurring tasks
        for task in self.recurring_tasks:
            if task["active"] and task["next_run"] <= current_time:
                try:
                    result = self.system.delegate(task["agent"], task["task"], task["context"])
                except Exception as e:
                    result = {"agent": task["agent"], "task": task["task"], "status": "error", "error": str(e)}
                task["next_run"] = current_time + task["interval"]
                results.append(result)

        return results

    def cancel_recurring(self, index: int):
        """Cancel a recurring task by index"""
        if 0 <= index < len(self.recurring_tasks):
            self.recurring_tasks[index]["active"] = False

    def get_scheduled_count(self) -> Dict[str, int]:
        """Get count of pending and recurring tasks"""
        return {
            "pending": sum(1 for t in self.scheduled_tasks if t["status"] == "pending"),
            "recurring_active": sum(1 for t in self.recurring_tasks if t["active"]),
            "recurring_inactive": sum(1 for t in self.recurring_tasks if not t["active"])
        }

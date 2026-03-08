from typing import Dict, Any, List
import time

class TaskScheduler:
    def __init__(self, system):
        self.system = system
        self.scheduled_tasks = []
        self.recurring_tasks = []
    
    def schedule(self, agent_name: str, task: str, delay: float, context: Dict = None):
        """Schedule task to run after delay (seconds)"""
        self.scheduled_tasks.append({
            "agent": agent_name,
            "task": task,
            "context": context,
            "execute_at": time.time() + delay,
            "status": "pending"
        })
    
    def schedule_recurring(self, agent_name: str, task: str, interval: float, context: Dict = None):
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
        """Execute all pending scheduled tasks"""
        current_time = time.time()
        results = []
        
        # Run scheduled tasks
        for task in self.scheduled_tasks:
            if task["status"] == "pending" and task["execute_at"] <= current_time:
                result = self.system.delegate(task["agent"], task["task"], task["context"])
                task["status"] = "completed"
                results.append(result)
        
        # Run recurring tasks
        for task in self.recurring_tasks:
            if task["active"] and task["next_run"] <= current_time:
                result = self.system.delegate(task["agent"], task["task"], task["context"])
                task["next_run"] = current_time + task["interval"]
                results.append(result)
        
        return results
    
    def cancel_recurring(self, index: int):
        if 0 <= index < len(self.recurring_tasks):
            self.recurring_tasks[index]["active"] = False

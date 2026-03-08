from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent import Agent
import time

class MultiAgentSystem:
    def __init__(self, max_workers: int = 10):
        self.agents: Dict[str, Agent] = {}
        self.shared_memory = {}
        self.event_log = []
        self.max_workers = max_workers
        self.middleware = []
    
    def add_agent(self, agent: Agent):
        self.agents[agent.name] = agent
        self.log_event("agent_added", {"agent": agent.name, "role": agent.role})
    
    def remove_agent(self, agent_name: str):
        if agent_name in self.agents:
            del self.agents[agent_name]
            self.log_event("agent_removed", {"agent": agent_name})
    
    def add_middleware(self, middleware: Callable):
        self.middleware.append(middleware)
    
    def delegate(self, agent_name: str, task: str, context: Dict = None, priority: int = 0) -> Dict:
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")
        
        # Apply middleware
        for mw in self.middleware:
            task, context = mw(agent_name, task, context)
        
        return self.agents[agent_name].process(task, context)
    
    def parallel_execute(self, tasks: List[Dict[str, str]], timeout: int = None) -> List[Dict]:
        with ThreadPoolExecutor(max_workers=min(len(tasks), self.max_workers)) as executor:
            futures = {
                executor.submit(
                    self.delegate, 
                    task["agent"], 
                    task["task"], 
                    task.get("context"),
                    task.get("priority", 0)
                ): task for task in tasks
            }
            
            results = []
            for future in as_completed(futures, timeout=timeout):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({"status": "error", "error": str(e)})
            
            return results
    
    def broadcast(self, task: str) -> List[Dict]:
        return [agent.process(task) for agent in self.agents.values()]
    
    def find_agent_by_capability(self, capability: str) -> List[Agent]:
        return [agent for agent in self.agents.values() if capability in agent.capabilities]
    
    def get_best_agent(self, capability: str) -> Agent:
        candidates = self.find_agent_by_capability(capability)
        if not candidates:
            raise ValueError(f"No agent with capability '{capability}'")
        return max(candidates, key=lambda a: (a.priority, a.get_metrics()["success_rate"]))
    
    def auto_delegate(self, task: str, capability: str, context: Dict = None) -> Dict:
        agent = self.get_best_agent(capability)
        return self.delegate(agent.name, task, context)
    
    def share_data(self, key: str, value: Any, ttl: int = None):
        self.shared_memory[key] = {
            "value": value, 
            "timestamp": time.time(),
            "expires_at": time.time() + ttl if ttl else None
        }
    
    def get_shared_data(self, key: str) -> Any:
        data = self.shared_memory.get(key)
        if data:
            if data["expires_at"] is None or data["expires_at"] > time.time():
                return data["value"]
        return None
    
    def log_event(self, event_type: str, data: Dict):
        self.event_log.append({"type": event_type, "data": data, "timestamp": time.time()})
    
    def get_system_status(self) -> Dict:
        return {
            "agents": {name: {
                "role": agent.role, 
                "state": agent.state,
                "tasks_completed": len(agent.task_history),
                "metrics": agent.get_metrics()
            } for name, agent in self.agents.items()},
            "shared_memory_keys": list(self.shared_memory.keys()),
            "total_events": len(self.event_log),
            "active_agents": sum(1 for a in self.agents.values() if a.state == "busy")
        }
    
    def get_agent_leaderboard(self) -> List[Dict]:
        return sorted([
            {"name": name, "metrics": agent.get_metrics()}
            for name, agent in self.agents.items()
        ], key=lambda x: x["metrics"]["success_rate"], reverse=True)

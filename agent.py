from typing import List, Dict, Any, Callable
import time

class Agent:
    def __init__(self, name: str, role: str, mcp_servers: List = None, capabilities: List[str] = None, priority: int = 0):
        self.name = name
        self.role = role
        self.mcp_servers = mcp_servers or []
        self.capabilities = capabilities or []
        self.priority = priority
        self.context = []
        self.memory = []
        self.task_history = []
        self.callbacks = []
        self.state = "idle"
        self.max_retries = 3
    
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
        self.memory.append({
            "key": key, 
            "value": value, 
            "timestamp": time.time(),
            "expires_at": time.time() + ttl if ttl else None
        })
    
    def recall(self, key: str) -> Any:
        current_time = time.time()
        for item in reversed(self.memory):
            if item["key"] == key:
                if item["expires_at"] is None or item["expires_at"] > current_time:
                    return item["value"]
        return None
    
    def forget(self, key: str):
        self.memory = [m for m in self.memory if m["key"] != key]
    
    def clear_memory(self):
        self.memory.clear()
    
    def process(self, task: str, context: Dict = None, retry: int = 0) -> Dict[str, Any]:
        self.state = "busy"
        start_time = time.time()
        self.context.append({"role": "user", "content": task})
        
        try:
            result = {
                "agent": self.name,
                "task": task,
                "status": "completed",
                "duration": time.time() - start_time,
                "context": context,
                "retry_count": retry
            }
        except Exception as e:
            if retry < self.max_retries:
                return self.process(task, context, retry + 1)
            result = {
                "agent": self.name,
                "task": task,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time,
                "retry_count": retry
            }
        
        self.task_history.append(result)
        self.state = "idle"
        
        for callback in self.callbacks:
            callback(result)
        
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

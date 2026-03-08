import json
from typing import Any, Callable, Dict
import time

class MCPServer:
    def __init__(self, name: str, description: str = "", rate_limit: int = None):
        self.name = name
        self.description = description
        self.tools = {}
        self.tool_metadata = {}
        self.execution_log = []
        self.rate_limit = rate_limit
        self.rate_limit_window = []
        self.cache = {}
        self.hooks = {"before": [], "after": []}
    
    def register_tool(self, name: str, func: Callable, description: str = "", params_schema: Dict = None, cacheable: bool = False):
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
            current_time = time.time()
            self.rate_limit_window = [t for t in self.rate_limit_window if current_time - t < 60]
            if len(self.rate_limit_window) >= self.rate_limit:
                raise Exception("Rate limit exceeded")
            self.rate_limit_window.append(current_time)
    
    def _get_cache_key(self, tool_name: str, params: dict) -> str:
        return f"{tool_name}:{json.dumps(params, sort_keys=True)}"
    
    def execute(self, tool_name: str, params: dict, use_cache: bool = True) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        self._check_rate_limit()
        
        # Check cache
        cache_key = self._get_cache_key(tool_name, params)
        if use_cache and self.tool_metadata[tool_name].get("cacheable") and cache_key in self.cache:
            return self.cache[cache_key]["result"]
        
        # Before hooks
        for hook in self.hooks["before"]:
            hook(tool_name, params)
        
        start_time = time.time()
        try:
            result = self.tools[tool_name](**params)
            status = "success"
            
            # Cache result
            if self.tool_metadata[tool_name].get("cacheable"):
                self.cache[cache_key] = {"result": result, "timestamp": time.time()}
        except Exception as e:
            result = str(e)
            status = "error"
        
        log_entry = {
            "tool": tool_name,
            "params": params,
            "result": result,
            "status": status,
            "duration": time.time() - start_time,
            "timestamp": time.time()
        }
        
        self.execution_log.append(log_entry)
        
        # After hooks
        for hook in self.hooks["after"]:
            hook(log_entry)
        
        if status == "error":
            raise Exception(result)
        
        return result
    
    def clear_cache(self):
        self.cache.clear()
    
    def list_tools(self) -> list:
        return list(self.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Dict:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self.tool_metadata.get(tool_name, {})
    
    def get_stats(self) -> Dict:
        total = len(self.execution_log)
        success = sum(1 for log in self.execution_log if log["status"] == "success")
        avg_duration = sum(log["duration"] for log in self.execution_log) / total if total > 0 else 0
        return {
            "server": self.name,
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration": avg_duration,
            "tools": len(self.tools),
            "cache_size": len(self.cache)
        }

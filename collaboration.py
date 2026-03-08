from typing import Dict, List, Any
import time

class AgentCollaboration:
    def __init__(self, system):
        self.system = system
        self.collaboration_history = []
    
    def negotiate(self, agents: List[str], task: str) -> str:
        """Select best agent through negotiation based on metrics"""
        candidates = [self.system.agents[name] for name in agents if name in self.system.agents]
        if not candidates:
            raise ValueError("No valid agents for negotiation")
        
        best = max(candidates, key=lambda a: (
            a.priority,
            a.get_metrics()["success_rate"],
            -len(a.task_history)
        ))
        return best.name
    
    def collaborate(self, agents: List[str], task: str) -> Dict:
        """Multiple agents work together on a task"""
        start_time = time.time()
        results = []
        
        for agent_name in agents:
            context = {"previous_results": results}
            result = self.system.delegate(agent_name, task, context)
            results.append(result)
        
        collaboration = {
            "agents": agents,
            "task": task,
            "results": results,
            "duration": time.time() - start_time
        }
        self.collaboration_history.append(collaboration)
        return collaboration
    
    def vote(self, agents: List[str], task: str, options: List[Any]) -> Any:
        """Agents vote on best option"""
        votes = {}
        for agent_name in agents:
            result = self.system.delegate(agent_name, f"{task}: {options}")
            choice = result.get("choice", options[0])
            votes[choice] = votes.get(choice, 0) + 1
        
        return max(votes.items(), key=lambda x: x[1])[0]

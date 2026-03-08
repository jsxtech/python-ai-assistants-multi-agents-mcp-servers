# Python AI Assistants - Multi-Agent System with MCP Servers

A minimal implementation of AI assistants using multi-agent architecture with Model Context Protocol (MCP) servers.

## Features

### 🤖 Agent System
- **Role-based agents** with specialized capabilities
- **Memory system** - agents can remember and recall information with TTL
- **Task history** - track all completed tasks
- **Callbacks** - hook into task completion events
- **Capability tagging** - find agents by their skills
- **Tool access** - agents can use MCP server tools
- **Priority levels** - prioritize agents for task selection
- **State management** - track agent status (idle/busy)
- **Auto-retry** - automatic retry on failures
- **Metrics** - success rate, duration, task counts
- **Learning** - agents learn from feedback and improve

### 🔧 MCP Servers
- **Tool registration** with metadata and descriptions
- **Execution logging** - track all tool invocations
- **Statistics** - monitor success/failure rates with averages
- **Error handling** - graceful failure management
- **Parameter schemas** - define tool interfaces
- **Caching** - cache tool results for performance
- **Rate limiting** - prevent server overload
- **Hooks** - before/after execution hooks
- **Tool metadata** - descriptions and schemas

### 🎯 Multi-Agent Orchestration
- **Delegation** - assign tasks to specific agents
- **Auto-delegation** - automatically select best agent by capability
- **Parallel execution** - run multiple agents simultaneously with timeouts
- **Broadcasting** - send tasks to all agents
- **Shared memory** - cross-agent data sharing with TTL
- **Event logging** - system-wide activity tracking
- **Status monitoring** - real-time system health
- **Middleware** - intercept and modify tasks
- **Leaderboard** - rank agents by performance
- **Load balancing** - distribute tasks efficiently

### 🔄 Workflow Engine
- **Sequential execution** - ordered task processing
- **Parallel workflows** - execute independent steps concurrently
- **Dependencies** - tasks wait for prerequisites
- **Context passing** - share results between steps
- **Multi-agent workflows** - coordinate different agents
- **Conditional steps** - execute based on conditions
- **Error handlers** - custom error handling per step
- **Retry logic** - automatic retry on failures
- **Workflow stats** - track execution metrics

### 🤝 Collaboration
- **Agent negotiation** - select best agent through negotiation
- **Multi-agent collaboration** - agents work together on tasks
- **Voting** - agents vote on decisions
- **Collaboration history** - track team efforts

### 📡 Event System
- **Event bus** - pub/sub messaging between components
- **Event subscriptions** - subscribe to specific events
- **Event history** - query past events
- **Event filtering** - filter by type and time

### ⏰ Scheduling
- **Delayed tasks** - schedule tasks for future execution
- **Recurring tasks** - periodic task execution
- **Task cancellation** - cancel scheduled tasks
- **Automatic execution** - run pending tasks

### 🛡️ Resilience
- **Circuit breaker** - prevent cascading failures
- **Load balancer** - distribute load across agents (round-robin, least-busy, best-performance)
- **Rate limiter** - control request rates
- **Retry logic** - automatic retries with backoff

### 💾 Persistence
- **State management** - save/load system state
- **Checkpoints** - create named snapshots
- **Metrics collection** - comprehensive metrics tracking
- **Export/import** - transfer knowledge between systems

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from mcp_server import MCPServer
from agent import Agent
from multi_agent_system import MultiAgentSystem

# Create MCP server with rate limiting
file_server = MCPServer("file_ops", "File operations", rate_limit=100)
file_server.register_tool("read", lambda path: f"Reading {path}", cacheable=True)

# Create agent with priority
coder = Agent("coder", "Code writer", [file_server], ["coding"], priority=1)

# Create system with max workers
system = MultiAgentSystem(max_workers=5)
system.add_agent(coder)

# Execute task
result = system.delegate("coder", "Write function")
print(result)
```

## Usage Examples

### Basic Agent Delegation
```python
result = system.delegate("researcher", "Find AI trends")
```

### Parallel Execution
```python
tasks = [
    {"agent": "researcher", "task": "Research topic A"},
    {"agent": "coder", "task": "Write module B"}
]
# With timeout
results = system.parallel_execute(tasks, timeout=30)
```

### Auto-Delegation
```python
# Automatically select best agent by capability
result = system.auto_delegate("Find research papers", "research")
print(f"Selected: {result['agent']}")
```

### Agent Leaderboard
```python
leaderboard = system.get_agent_leaderboard()
for rank, entry in enumerate(leaderboard, 1):
    print(f"{rank}. {entry['name']}: {entry['metrics']['success_rate']:.2%}")
```

### Agent Memory
```python
# Basic memory
agent.remember("key", "value")
value = agent.recall("key")

# Memory with TTL (expires after 60 seconds)
agent.remember("temp_key", "temp_value", ttl=60)

# Memory management
agent.forget("key")
agent.clear_memory()
```

### Shared Memory
```python
# Basic shared memory
system.share_data("project_name", "AI Assistant")
data = system.get_shared_data("project_name")

# Shared memory with TTL
system.share_data("session_id", "abc123", ttl=3600)
```

### Broadcasting
```python
results = system.broadcast("Status check")
```

### Find by Capability
```python
web_agents = system.find_agent_by_capability("web")
```

### Workflows with Dependencies
```python
from workflow import Workflow

workflow = Workflow("pipeline", max_retries=3)
workflow.add_step("researcher", "Gather data")
workflow.add_step("analyst", "Process data", depends_on=[0])
workflow.add_step("coder", "Generate report", depends_on=[1])

# Sequential execution
results = workflow.execute(system)

# Parallel execution (by dependency levels)
results = workflow.execute(system, parallel=True)

# Conditional steps
workflow.add_step("notifier", "Send alert", 
                  condition=lambda r: r.get(0, {}).get("status") == "completed")

# Error handlers
workflow.add_error_handler(0, lambda e, step, ctx: {"status": "recovered"})

# Workflow stats
stats = workflow.get_stats()
print(f"Avg duration: {stats['avg_duration']:.3f}s")
```

### Callbacks
```python
def on_complete(result):
    print(f"Task done: {result['task']}")

agent.add_callback(on_complete)
```

### MCP Tool Usage
```python
result = agent.use_tool("file_ops", "read", {"path": "/data.txt"})
```

### System Status
```python
status = system.get_system_status()
print(status)
```

### MCP Server Stats
```python
stats = server.get_stats()
print(f"Total executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Avg duration: {stats['avg_duration']:.3f}s")
print(f"Cache size: {stats['cache_size']}")
```

### MCP Server Hooks
```python
def before_hook(tool_name, params):
    print(f"Executing {tool_name}")

def after_hook(log_entry):
    print(f"Completed in {log_entry['duration']:.3f}s")

server.add_hook("before", before_hook)
server.add_hook("after", after_hook)
```

### Agent Metrics
```python
metrics = agent.get_metrics()
print(f"Total tasks: {metrics['total_tasks']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Avg duration: {metrics['avg_duration']:.3f}s")
```

## Architecture

```
MultiAgentSystem
├── Agent (researcher)
│   ├── Memory
│   ├── Callbacks
│   └── MCP Servers
│       └── web_operations
├── Agent (coder)
│   └── MCP Servers
│       └── file_operations
└── Agent (analyst)
    └── MCP Servers
        ├── file_operations
        └── web_operations
```

## Components

### Agent (`agent.py`)
Individual AI assistant with role, capabilities, memory, and MCP server access.

### MCPServer (`mcp_server.py`)
Tool provider that registers and executes functions with logging and stats.

### MultiAgentSystem (`multi_agent_system.py`)
Orchestrates multiple agents with delegation, parallel execution, and shared state.

### Workflow (`workflow.py`)
Manages sequential task execution with dependency resolution.

## Run Examples

### Basic Example
```bash
python example.py
```

### Advanced Features
```bash
python advanced_example.py
```

## Advanced Usage

### Agent Learning
```python
from learning import AgentLearning

learning = AgentLearning(agent)
learning.learn_from_feedback("Research task", "Excellent", 5.0)
best_tasks = learning.get_best_task_types()

# Export/import knowledge
knowledge = learning.export_knowledge()
learning.import_knowledge(knowledge)
```

### Collaboration
```python
from collaboration import AgentCollaboration

collab = AgentCollaboration(system)

# Negotiate best agent
best = collab.negotiate(["agent1", "agent2"], "Complex task")

# Collaborate on task
result = collab.collaborate(["agent1", "agent2"], "Team task")

# Voting
choice = collab.vote(["agent1", "agent2"], "Pick option", ["A", "B", "C"])
```

### Event Bus
```python
from event_bus import EventBus

bus = EventBus()

# Subscribe to events
bus.subscribe("task_complete", lambda e: print(e))

# Publish events
bus.publish("task_complete", {"task": "done"})

# Query event history
events = bus.get_events(event_type="task_complete", since=time.time()-3600)
```

### Scheduling
```python
from scheduler import TaskScheduler

scheduler = TaskScheduler(system)

# Delayed task (run after 10 seconds)
scheduler.schedule("agent", "Task", delay=10)

# Recurring task (run every 60 seconds)
scheduler.schedule_recurring("agent", "Task", interval=60)

# Execute pending tasks
results = scheduler.run_pending()

# Cancel recurring task
scheduler.cancel_recurring(0)
```

### Load Balancing
```python
from resilience import LoadBalancer

balancer = LoadBalancer(system)

# Set strategy: round_robin, least_busy, best_performance
balancer.set_strategy("best_performance")
agent = balancer.select_agent("capability")
```

### Circuit Breaker
```python
from resilience import CircuitBreaker

breaker = CircuitBreaker(failure_threshold=5, timeout=60)

# Protected call
result = breaker.call(system.delegate, "agent", "task")
print(f"Circuit state: {breaker.state}")  # closed, open, half-open
```

### Rate Limiter
```python
from resilience import RateLimiter

limiter = RateLimiter(max_requests=10, window=60)

if limiter.allow():
    # Process request
    pass
else:
    wait = limiter.wait_time()
    print(f"Rate limited, wait {wait:.1f}s")
```

### State Management
```python
from persistence import StateManager

manager = StateManager("state.json")

# Save current state
manager.save_state(system)

# Create checkpoint
manager.checkpoint(system, "backup1")

# Load state
state = manager.load_state()

# Restore from checkpoint
state = manager.restore_checkpoint("backup1")
```

### Metrics Collection
```python
from persistence import MetricsCollector

metrics = MetricsCollector()

# Record task execution
metrics.record("agent", result)

# Get summary
summary = metrics.get_summary()
print(f"Success rate: {summary['success_rate']:.2%}")
print(f"Avg duration: {summary['avg_duration']:.3f}s")

# Reset metrics
metrics.reset()
```

## API Reference

### Agent
```python
Agent(name, role, mcp_servers=[], capabilities=[], priority=0)
  .remember(key, value, ttl=None)
  .recall(key) -> value
  .forget(key)
  .clear_memory()
  .use_tool(server_name, tool_name, params)
  .process(task, context=None)
  .get_metrics() -> dict
  .get_available_tools() -> dict
```

### MCPServer
```python
MCPServer(name, description="", rate_limit=None)
  .register_tool(name, func, description="", params_schema=None, cacheable=False)
  .add_hook(hook_type, func)  # "before" or "after"
  .execute(tool_name, params, use_cache=True)
  .clear_cache()
  .get_stats() -> dict
  .list_tools() -> list
```

### MultiAgentSystem
```python
MultiAgentSystem(max_workers=10)
  .add_agent(agent)
  .remove_agent(agent_name)
  .delegate(agent_name, task, context=None, priority=0)
  .auto_delegate(task, capability, context=None)
  .parallel_execute(tasks, timeout=None)
  .broadcast(task)
  .find_agent_by_capability(capability)
  .get_best_agent(capability)
  .share_data(key, value, ttl=None)
  .get_shared_data(key)
  .get_system_status() -> dict
  .get_agent_leaderboard() -> list
  .add_middleware(middleware_func)
```

### Workflow
```python
Workflow(name, max_retries=3)
  .add_step(agent_name, task, depends_on=[], condition=None)
  .add_error_handler(step_id, handler)
  .execute(system, parallel=False)
  .get_stats() -> dict
```

## License

MIT

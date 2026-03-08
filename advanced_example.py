from mcp_server import MCPServer
from agent import Agent
from multi_agent_system import MultiAgentSystem
from workflow import Workflow
from collaboration import AgentCollaboration
from event_bus import EventBus
from scheduler import TaskScheduler
from learning import AgentLearning
from resilience import CircuitBreaker, LoadBalancer, RateLimiter
from persistence import StateManager, MetricsCollector

# Create MCP servers
file_server = MCPServer("file_operations", "File system operations", rate_limit=100)
file_server.register_tool("read", lambda path: f"Reading {path}", "Read file", cacheable=True)
file_server.register_tool("write", lambda path, content: f"Writing to {path}", "Write file")

web_server = MCPServer("web_operations", "Web operations", rate_limit=50)
web_server.register_tool("fetch", lambda url: f"Fetching {url}", "Fetch URL", cacheable=True)

# Add hooks
def log_tool_execution(tool_name, params):
    print(f"[HOOK] Executing {tool_name} with {params}")

file_server.add_hook("before", log_tool_execution)

# Create agents with priorities
researcher = Agent("researcher", "Research specialist", [web_server], ["research", "web"], priority=2)
coder = Agent("coder", "Code specialist", [file_server], ["coding", "files"], priority=3)
analyst = Agent("analyst", "Data analyst", [file_server, web_server], ["analysis", "data"], priority=1)

# Add learning
researcher_learning = AgentLearning(researcher)
researcher_learning.learn_from_feedback("Research AI trends", "Great work", 4.5)

# Create system with advanced features
system = MultiAgentSystem(max_workers=5)
system.add_agent(researcher)
system.add_agent(coder)
system.add_agent(analyst)

# Event bus
event_bus = EventBus()
def on_task_complete(event):
    print(f"[EVENT] Task completed: {event['data']}")

event_bus.subscribe("task_complete", on_task_complete)

# Collaboration
collab = AgentCollaboration(system)
print("\n=== Agent Negotiation ===")
best_agent = collab.negotiate(["researcher", "analyst"], "Analyze web data")
print(f"Selected agent: {best_agent}")

print("\n=== Agent Collaboration ===")
collab_result = collab.collaborate(["researcher", "analyst"], "Research and analyze AI trends")
print(f"Collaboration completed with {len(collab_result['results'])} agents")

# Scheduler
scheduler = TaskScheduler(system)
scheduler.schedule("researcher", "Scheduled research task", delay=0.1)
scheduler.schedule_recurring("analyst", "Periodic analysis", interval=1)

print("\n=== Running Scheduled Tasks ===")
scheduled_results = scheduler.run_pending()
print(f"Executed {len(scheduled_results)} scheduled tasks")

# Load balancer
load_balancer = LoadBalancer(system)
load_balancer.set_strategy("best_performance")
print("\n=== Load Balancing ===")
selected = load_balancer.select_agent("research")
print(f"Load balancer selected: {selected}")

# Circuit breaker
circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=5)
print("\n=== Circuit Breaker ===")
try:
    result = circuit_breaker.call(system.delegate, "researcher", "Protected task")
    print(f"Circuit breaker: {circuit_breaker.state}")
except Exception as e:
    print(f"Circuit breaker error: {e}")

# Rate limiter
rate_limiter = RateLimiter(max_requests=10, window=60)
print("\n=== Rate Limiter ===")
for i in range(3):
    if rate_limiter.allow():
        print(f"Request {i+1} allowed")
    else:
        print(f"Request {i+1} blocked, wait {rate_limiter.wait_time():.2f}s")

# Metrics
metrics = MetricsCollector()
result = system.delegate("researcher", "Test task")
metrics.record("researcher", result)
print("\n=== Metrics Summary ===")
print(metrics.get_summary())

# State management
state_manager = StateManager("system_state.json")
print("\n=== State Management ===")
state_manager.save_state(system)
state_manager.checkpoint(system, "backup1")
print("State saved and checkpoint created")

# Auto-delegation
print("\n=== Auto-Delegation ===")
auto_result = system.auto_delegate("Find research papers", "research")
print(f"Auto-delegated to best agent: {auto_result['agent']}")

# Agent leaderboard
print("\n=== Agent Leaderboard ===")
leaderboard = system.get_agent_leaderboard()
for rank, entry in enumerate(leaderboard, 1):
    print(f"{rank}. {entry['name']}: {entry['metrics']['success_rate']:.2%} success rate")

# Workflow with conditions
print("\n=== Conditional Workflow ===")
workflow = Workflow("conditional_pipeline", max_retries=2)
workflow.add_step("researcher", "Gather data")
workflow.add_step("analyst", "Analyze if data exists", depends_on=[0], 
                  condition=lambda r: r.get(0, {}).get("status") == "completed")
workflow.add_step("coder", "Generate report", depends_on=[1])

workflow_results = workflow.execute(system)
print(f"Workflow completed: {len(workflow_results)} steps")
print(f"Workflow stats: {workflow.get_stats()}")

# System status
print("\n=== System Status ===")
status = system.get_system_status()
print(f"Active agents: {status['active_agents']}/{len(status['agents'])}")
print(f"Total events: {status['total_events']}")

# MCP server stats
print("\n=== MCP Server Stats ===")
print(file_server.get_stats())
print(web_server.get_stats())

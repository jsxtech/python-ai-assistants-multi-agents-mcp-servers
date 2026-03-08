from mcp_server import MCPServer
from agent import Agent
from multi_agent_system import MultiAgentSystem
from workflow import Workflow

# Create MCP servers with enhanced metadata
file_server = MCPServer("file_operations", "File system operations")
file_server.register_tool("read", lambda path: f"Reading {path}", "Read file content")
file_server.register_tool("write", lambda path, content: f"Writing to {path}", "Write to file")

web_server = MCPServer("web_operations", "Web and API operations")
web_server.register_tool("fetch", lambda url: f"Fetching {url}", "Fetch URL content")

# Create agents with capabilities
researcher = Agent("researcher", "Research and gather information", [web_server], ["research", "web"])
coder = Agent("coder", "Write and modify code", [file_server], ["coding", "files"])
analyst = Agent("analyst", "Analyze data", [file_server, web_server], ["analysis", "data"])

# Add callback
def on_task_complete(result):
    print(f"✓ {result['agent']} completed in {result['duration']:.3f}s")

researcher.add_callback(on_task_complete)

# Create multi-agent system
system = MultiAgentSystem()
system.add_agent(researcher)
system.add_agent(coder)
system.add_agent(analyst)

# Basic delegation
print("\n=== Basic Delegation ===")
result = system.delegate("researcher", "Find information about AI")
print(result)

# Parallel execution
print("\n=== Parallel Execution ===")
tasks = [
    {"agent": "researcher", "task": "Research topic A"},
    {"agent": "coder", "task": "Write module B"},
    {"agent": "analyst", "task": "Analyze data C"}
]
results = system.parallel_execute(tasks)
print(f"Completed {len(results)} tasks")

# Broadcast to all agents
print("\n=== Broadcast ===")
broadcast_results = system.broadcast("Status check")
print(f"Broadcast to {len(broadcast_results)} agents")

# Find agents by capability
print("\n=== Find by Capability ===")
web_agents = system.find_agent_by_capability("web")
print(f"Agents with 'web' capability: {[a.name for a in web_agents]}")

# Shared memory
print("\n=== Shared Memory ===")
system.share_data("project_name", "AI Assistant")
print(f"Shared data: {system.get_shared_data('project_name')}")

# Agent memory
print("\n=== Agent Memory ===")
researcher.remember("last_search", "AI trends 2026")
print(f"Recalled: {researcher.recall('last_search')}")

# Workflow with dependencies
print("\n=== Workflow ===")
workflow = Workflow("data_pipeline")
workflow.add_step("researcher", "Gather data sources")
workflow.add_step("analyst", "Process data", depends_on=[0])
workflow.add_step("coder", "Generate report", depends_on=[1])
workflow_results = workflow.execute(system)
print(f"Workflow completed {len(workflow_results)} steps")

# System status
print("\n=== System Status ===")
status = system.get_system_status()
print(status)

# MCP server stats
print("\n=== MCP Server Stats ===")
print(file_server.get_stats())
print(web_server.get_stats())

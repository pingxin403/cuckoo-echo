# Multi-Agent Orchestration Specification

## Overview

Enable multiple specialized AI agents to coordinate on complex tasks with hierarchical or flat orchestration patterns, shared context propagation, and fault tolerance.

## Background

Current system: Single agent with tool execution. Research shows:
- Multi-agent systems achieve better specialization and parallelism
- Three-layer memory model (global → group → individual) is converging
- Coordination patterns: Hierarchical (Orchestrator + Workers) vs Flat (peers)

## Goals

1. Support multi-agent workflows with role-based specialization
2. Enable inter-agent communication and shared context
3. Provide fault tolerance and recovery
4. Add observability across agent boundaries

## Technical Approach

### Architecture

```yaml
Layer 5: Orchestration Layer     # Multi-agent coordination
Layer 4: Agent Execution Layer  # Reasoning, planning, action
Layer 3: Tool & Integration    # External system connections
Layer 2: Memory & Context     # State management, knowledge
Layer 1: LLM Base            # Foundation model
```

### Agent Roles

- Orchestrator: Task decomposition, delegation, result aggregation
- Specialist: Domain-specific reasoning (RAG, code, analysis)
- Coordinator: Cross-agent communication routing

### Coordination Patterns

1. Hierarchical: Orchestrator dispatches to worker agents
2. Flat: Peer agents withshared message bus
3. Sequential: Pipeline of specialized agents

### Inter-Agent Protocol

```python
@dataclass
class AgentMessage:
    sender: str
    receiver: str
    content: Any
    trace_id: str
    timestamp: float
    message_type: MessageType  # REQUEST, RESPONSE, BROADCAST
```

### Shared Memory Layers

- Global: Team-wide knowledge (Redis)
- Group/Role: Task-scoped context
- Individual: Per-agent working memory

## Implementation

### Files

1. `chat_service/agent/orchestrator.py` - MultiAgentOrchestrator class
2. `chat_service/agent/agent_message.py` - Message protocol
3. `chat_service/agent/shared_context.py` - Inter-agent context
4. `chat_service/agent/role_registry.py` - Agent role management

### Key Classes

```python
class MultiAgentOrchestrator:
    async def run_workflow(self, workflow: Workflow) -> AgentResult:
    async def delegate_task(self, agent_id: str, task: Task) -> AgentResult:
    async def aggregate_results(self, results: list[AgentResult]) -> str:
```

## Acceptance Criteria

- [x] Orchestrator delegates to multiple specialist agents
- [x] Agent messages propagate context
- [x] Shared memory accessible across agents
- [x] Fault tolerance with retry/fallback
- [x] Step-level tracing across agents
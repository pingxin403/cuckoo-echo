# Proposal: Add Agent Tooling

## Summary

Add debugging, observability, and control tooling for AI agents in production.

## Problem

- No visibility into agent reasoning
- No way to debug conversation flows
- No human-in-loop controls

## Solution

### P0 - Agent Debugging

- **/debug/agent/state**: Inspect agent graph state
- **/debug/agent/history**: Agent reasoning history
- **/debug/node/{node_id}**: Per-node inspection

### P1 - Flow Control

- **/debug/node/{node_id}/execute**: Execute single node
- **/debug/node/{node_id}/skip**: Skip node execution
- **/debug/node/{node_id}/modify**: Modify node output

### P2 - Observability

- **Reasoning traces**: Full LLM reasoning export
- **Token breakdown**: Per-node token usage
- **Cost tracking**: Per-conversation cost

## Priority

P0 - Production debugging

## Impact

- Faster debugging
- Better support
- Cost visibility
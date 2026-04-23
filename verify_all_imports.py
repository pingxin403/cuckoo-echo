"""Final verification script to ensure all modules compile and import correctly."""

import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

SHARED_MODULES = [
    "shared.citation",
    "shared.query_rewriting",
    "shared.reasoning",
    "shared.prompt_template",
    "shared.prompt_factory",
    "shared.prompt_versioning",
    "shared.semantic_chunker",
    "shared.hybrid_search",
    "shared.reranker",
    "shared.context_optimizer",
    "shared.guardrails",
    "shared.pii_detector",
    "shared.action_policy",
    "shared.output_filter",
    "shared.context_compressor",
    "shared.retry",
    "shared.circuit_breaker",
    "shared.architecture_docs",
    "shared.webhook_service",
    "shared.sso_auth",
    "shared.channel_adapters",
    "shared.rbac",
    "shared.customer_success",
    "shared.api_marketplace",
    "shared.plugin_system",
    "shared.knowledge_gap",
    "shared.analytics",
    "shared.translation",
    "shared.billing",
    "shared.semantic_cache",
    "shared.redis_client",
    "shared.milvus_client",
    "shared.embedding_service",
    "shared.logging",
    "shared.metrics",
    "shared.memory_store",
    "shared.config",
    "shared.whisper_client",
    "shared.db",
    "shared.oss_client",
]

AGENT_MODULES = [
    "chat_service.agent.state",
    "chat_service.agent.intent_recognition",
    "chat_service.agent.state_machine",
    "chat_service.agent.memory_manager",
    "chat_service.agent.semantic_memory",
    "chat_service.agent.episodic_memory",
    "chat_service.agent.tool_registry",
    "chat_service.agent.tool_executor",
    "chat_service.agent.mcp_client",
    "chat_service.agent.shared_context",
    "chat_service.agent.agent_message",
    "chat_service.agent.summarizer",
    "chat_service.agent.checkpointer",
    "chat_service.agent.graph",
    "chat_service.agent.nodes.router",
    "chat_service.agent.nodes.preprocess",
    "chat_service.agent.nodes.rag_engine",
    "chat_service.agent.nodes.llm_generate",
    "chat_service.agent.nodes.guardrails",
    "chat_service.agent.nodes.hitl_node",
]

SERVICE_MODULES = [
    "chat_service.services.experiment",
    "chat_service.services.feedback",
    "chat_service.services.evaluation",
    "chat_service.services.rollout",
]

ROUTE_MODULES = [
    "chat_service.routes.chat",
    "chat_service.routes.ws_chat",
    "chat_service.routes.experiment",
    "chat_service.routes.feedback",
]

def test_import(module_name: str) -> tuple[bool, str]:
    try:
        __import__(module_name)
        return True, "OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def main():
    all_modules = SHARED_MODULES + AGENT_MODULES + SERVICE_MODULES + ROUTE_MODULES

    print("=" * 70)
    print("FINAL VERIFICATION REPORT")
    print("=" * 70)

    passed = 0
    failed = 0
    failed_modules = []

    for module in all_modules:
        success, message = test_import(module)
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {module:<45} {message}")
        if success:
            passed += 1
        else:
            failed += 1
            failed_modules.append((module, message))

    print("=" * 70)
    print(f"Total: {len(all_modules)}, Passed: {passed}, Failed: {failed}")
    print("=" * 70)

    if failed_modules:
        print("\nFAILED MODULES:")
        for module, message in failed_modules:
            print(f"  - {module}: {message}")
        return 1

    print("\nALL MODULES VERIFIED SUCCESSFULLY!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
# Tasks

## Phase 1: Configuration
- [ ] 1.1 Add LLM_TIMEOUT_SECONDS to config
- [ ] 1.2 Add timeout_seconds to tenant config schema
- [ ] 1.3 Read timeout from tenant config or default

## Phase 2: Timeout Handling
- [ ] 2.1 Wrap AI Gateway call in asyncio.wait_for
- [ ] 2.2 Catch TimeoutError exception
- [ ] 2.3 Return timeout error message

## Phase 3: Metrics
- [ ] 3.1 Track timeout count per tenant
- [ ] 3.2 Add llm_timeout_total counter
- [ ] 3.3 Include in health response

## Phase 4: User Experience
- [ ] 4.1 Show timeout message to user
- [ ] 4.2 Suggest retry option
- [ ] 4.3 Log timeout for debugging
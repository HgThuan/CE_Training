# AI Shopping Assistant

## Scope and request flow

The assistant remains inside the existing `apps.ai` module of the modular monolith. Its runtime
flow is:

```text
authenticated Customer + message
  -> structured query understanding
  -> versioned conversation-state merge
  -> missing-information policy and task planner
  -> allowlisted domain tools
  -> grounded recommendation and response composer
  -> attachment/product-ID validator
  -> persisted message + SSE response
```

The LLM is used only for schema-constrained language understanding. Deterministic Vietnamese
extraction remains available when the provider is disabled, times out, or returns malformed JSON.
Price, inventory, voucher, order, and policy facts always come from domain selectors or verified
database rows. The assistant has no raw SQL or arbitrary ORM tool.

## Conversation state and clarification

`ChatSession.context.assistant_state` uses an explicit schema version. Facts, inferences,
constraints, preferences, and exclusions are separate maps. Every value records source, turn, and
confidence. New explicit values replace prior values, including corrections such as a bounded
budget after “không giới hạn”. Short follow-ups such as “Chỉ Samsung thôi” narrow the current goal
without replacing its product query.

The planner computes missing information from the merged state rather than a fixed dialogue flow.
It asks at most two fields above `AI_ASSISTANT_CLARIFICATION_THRESHOLD`. An underspecified gift
request asks for high-value interest/budget information and does not return a random product.
When useful work is already safe, the response can educate, search, recommend, and clarify in the
same turn.

Situational discovery requests do not use the whole sentence as a literal product name. A small,
reviewable rule set preserves the explicit usage (for example, `đi biển`) and expands it into
catalog evidence such as `kem chống nắng`, `chống nước`, or `hoạt động ngoài trời`. Results still
come only from public, in-stock product rows, and the response names the expansion it used. Budget
is optional for this exploratory mode; a later answer such as `không giới hạn` updates the state
without replacing the usage or original search context.

## Tool and authorization boundary

The registry accepts only declared arguments for:

- `search_products` and `compare_products`;
- `get_policy` using active `PolicyDocument` rows, with pgvector retrieval and relational fallback;
- `get_order_status`, `get_return_support`, and `get_payment_support` using Customer-scoped order
  selectors;
- `get_promotions` using current relational validity/quantity checks;
- `get_flash_sales` using active/upcoming campaign timestamps and a server-side remaining-time
  calculation;
- `human_handoff`, which stores a sanitized context snapshot.

The API is Customer-only and every conversation/message lookup includes the authenticated owner.
The registry repeats Customer eligibility checks for account tools, so authorization does not
depend on a prompt or model decision. A prompt-injection guard refuses requests for system prompts,
secrets, raw SQL, or other users' data before any tool call.

## API and SSE contract

```http
POST   /api/v1/ai/assistant/messages
GET    /api/v1/ai/assistant/conversations/
GET    /api/v1/ai/assistant/conversations/{id}/
DELETE /api/v1/ai/assistant/conversations/{id}/
POST   /api/v1/ai/assistant/messages/{id}/feedback
```

The message endpoint emits `conversation`, `stage`, `delta`, `error`, and `done` SSE events. Stage
values are `understanding`, `planning`, `retrieving`, and `composing`. The final message contains
only allowlisted attachments grounded in successful tool results: product, comparison, order,
promotion, clarification, suggested reply, quick action, or handoff.

## Configuration

The global `AI_FEATURES_ENABLED` and `feature.ai_assistant.enabled` site setting must both be true.
The following environment settings tune behavior without distributing magic constants:

- `AI_ASSISTANT_RESULT_LIMIT`
- `AI_ASSISTANT_CLARIFICATION_THRESHOLD`
- `AI_ASSISTANT_RANK_CATEGORY_WEIGHT`
- `AI_ASSISTANT_RANK_BRAND_WEIGHT`
- `AI_ASSISTANT_RANK_PRICE_WEIGHT`
- `AI_ASSISTANT_RANK_PREFERENCE_WEIGHT`
- `AI_ASSISTANT_RANK_RATING_WEIGHT`
- `AI_ASSISTANT_RANK_STOCK_WEIGHT`
- `AI_ASSISTANT_RANK_INCOMPATIBILITY_PENALTY`

Policy vectors can be rebuilt with `python manage.py reindex_policy_embeddings`. Live catalog,
inventory, order, and promotion facts are deliberately not served from vector storage or a long
TTL cache.

## Failure and observability

Malformed structured output falls back to deterministic extraction. Tool failures become a safe
public message and do not expose an exception. An orchestration failure persists a fallback
assistant response where possible. `AIRequestLog` records conversation ID, intent, goals, plan,
tool status/latency, clarification fields, grounded product IDs, overall latency, and failure type;
credentials and raw chain-of-thought are never recorded.

The frontend supports authenticated history, SSE stages, grounded product explanations,
compatibility warnings, server-provided clarification suggestions, retry, errors, and feedback.
Guests see a login action rather than a non-persistent guest conversation.

## Verification

```bash
cd ecommerce/backend
TEST_USE_SQLITE=true .venv/bin/pytest apps/ai/tests -q

cd ../frontend
npm run test -- --run src/features/ai-chat
npm run lint
npm run build
```

Scenario coverage includes normal compound search, underspecified gifts, compound/open/negative
slot answers, situational discovery, Flash Sale duration, multi-task queries, multi-turn
corrections, empty results, product incompatibility, malformed/offline LLM fallback, prompt
injection, RBAC/ownership, streaming, history, and feedback.

# AI app

`apps.ai` is the provider-neutral boundary for smart search, semantic search, embeddings,
recommendations, and the multi-turn shopping assistant. Most callers use `AIService`; streaming
conversation orchestration lives in `AIChatService`, which still consumes the same provider
interface instead of importing a concrete provider.

## Shopping assistant

- `POST /api/v1/chat/turn` accepts `message`, an optional `session_id`, and a stable
  `guest_token`. It returns Server-Sent Events (`session`, `delta`, `error`, and `done`).
- `GET /api/v1/chat/sessions/<session_id>/messages` restores user/assistant history. A guest
  session can be claimed by the authenticated user only when the original guest token matches.
- `AIChatService` retains the latest 10 turns, summarizes older context, caps a session at 30
  user turns, and allows at most 5 function-calling rounds per turn.
- The model can search public in-stock products, retrieve a current product, compare 2–4
  products, and retrieve verified policy documents. Product cards and comparison tables are
  emitted only for product IDs returned by those tools during the current turn.
- The storefront/customer widget consumes the SSE response incrementally and reuses the existing
  `ProductCard` and `ProductCompareTable` components. The assistant never creates an order or
  makes a refund/discount commitment.

Policy answers come only from active `PolicyDocument` rows. The seed migration records the
shipping, return, and payment behavior implemented by the platform; it intentionally does not
invent a warranty policy or a fixed delivery SLA. Admins can maintain these documents in Django
admin. To build missing vector embeddings after policy changes, run:

```bash
python manage.py reindex_policy_embeddings
```

Use `--force` to replace existing policy vectors. Without embeddings, on SQLite, or when the AI
provider is unavailable, policy lookup falls back to the same verified rows by category/keyword.

## Search API

- `GET /api/v1/ai/smart-search/` extracts structured intent and combines it with the existing
  keyword/full-text search. Explicit client filters always override AI-inferred filters.
- `GET /api/v1/ai/semantic-search/` uses cosine distance on PostgreSQL embeddings and a small
  rating weight. Public Product, Shop, Category, and positive-stock filters remain authoritative.
- Both endpoints accept the public search filter whitelist, paginate with the standard paginator,
  and return `results`, `explanation`, `intent`, `ai_used`, and `fallback_used`.
- Anonymous and authenticated requests use separate throttle buckets.

The global `AI_FEATURES_ENABLED` switch and the cached
`feature.ai_search.enabled` `SiteSetting` must both be enabled. Disabled flags, provider errors,
invalid/non-finite vectors, SQLite, a missing vector extension, or an empty index degrade to
keyword search without exposing non-public products.

## Embedding indexing

Approved public products are indexed from deterministic normalized title, description, category,
brand, and attribute text. A SHA-256 content hash skips unchanged content; a successful re-index
removes older embeddings for that product/model.

Product saves dispatch `index_product_embedding` with `transaction.on_commit` only when both the
feature and provider are ready. The task checks those conditions again so a queued task cannot
call the provider after an administrator disables AI.

Initial indexing can be queued with:

```bash
python manage.py reindex_all_embeddings
```

Use `--sync` only for controlled maintenance. PostgreSQL with the `vector` extension is required
to validate vector ranking and HNSW behavior; the SQLite test suite intentionally verifies the
keyword fallback path instead.

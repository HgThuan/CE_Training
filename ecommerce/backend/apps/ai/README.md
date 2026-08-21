# AI app

`apps.ai` is the provider-neutral boundary for smart search, semantic search, embeddings,
recommendations, and the multi-turn shopping assistant. Most callers use `AIService`; streaming
conversation orchestration lives in `AIChatService`, which still consumes the same provider
interface instead of importing a concrete provider.

## Shopping assistant

- `POST /api/v1/chat/turn` accepts `message`, an optional `session_id`, a stable
  `guest_token`, up to 20 public product IDs in `browsing_history`, and a channel identifier.
  It returns Server-Sent Events (`session`, `delta`, `error`, and `done`). The same contract can
  be used by web, app, Zalo, Messenger, Telegram, or another adapter.
- `GET /api/v1/chat/sessions/<session_id>/messages` restores user/assistant history. A guest
  session can be claimed by the authenticated user only when the original guest token matches.
- `AIChatService` retains the latest 10 turns, summarizes older context, caps a session at 30
  user turns, and allows at most 5 function-calling rounds per turn.
- The model can search public in-stock products, retrieve a current product, compare 2–4
  products, and retrieve verified policy documents. Deterministic support routing handles order,
  return, payment, promotion, and personalized-recommendation intents without asking the model
  to invent or repeat operational data. Account tools require an authenticated customer and
  always scope queries to that customer.
- The storefront/customer widget consumes the SSE response incrementally and reuses the existing
  `ProductCard` and `ProductCompareTable` components. It also renders order, promotion, handoff,
  and quick-action cards. The assistant never creates an order, return, or payment transaction;
  state-changing actions remain on authenticated confirmation screens.
- `POST /api/v1/chat/messages/<message_id>/feedback` records a 1–5 rating and whether the issue
  was resolved. Ownership checks are identical to history access for both users and guests.
- A request to meet an employee creates a `ChatHandoff`, stores a sanitized 20-message context
  snapshot, and marks the session escalated. Staff can triage and assign handoffs in Django admin.
- `GET /api/v1/admin/dashboard/chatbot?days=30` reports response time, feedback rate, CSAT,
  automated resolution, handoff rate, and results by stable A/B variant.

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

- `GET /api/v1/ai/smart-search/` runs a separate NLU stage before catalog lookup. Its stable
  schema contains `intent_type`, `keywords`, and slots for `category_hints`, `price_range`,
  `attributes`, `occasion`, and `recipient`. Explicit client filters always override inferred
  values.
- A reviewable semantic rule layer handles vague Vietnamese needs. For example, “quà sinh nhật
  cho bạn gái” maps to non-authoritative hints such as mỹ phẩm, trang sức, phụ kiện, nước hoa,
  and túi xách. These hints broaden discovery but never masquerade as user-supplied filters.
- `explanation` and per-product `match_reasons` are controlled templates assembled from validated
  slots and actual catalog fields. Free-form model explanations are discarded, so price,
  category, and attribute claims cannot be hallucinated.
- `GET /api/v1/ai/semantic-search/` combines PostgreSQL full-text/BM25-like keyword rank with
  cosine-vector rank using reciprocal rank fusion:

  `score = 0.65 / (60 + semantic_rank) + 0.35 / (60 + keyword_rank)`

  The weights and RRF constant are configurable with `AI_SEARCH_SEMANTIC_WEIGHT`,
  `AI_SEARCH_KEYWORD_WEIGHT`, and `AI_SEARCH_RRF_K`. Candidates below
  `AI_SEARCH_MIN_COSINE_SIMILARITY` (default `0.30`) are rejected. A deterministic top-k
  re-ranker then uses only verified category match, rating, and sales fields. A learned
  cross-encoder can replace this re-ranker later without changing the endpoint contract.
- Both endpoints accept the public search filter whitelist, paginate with the standard paginator,
  and return `results`, `explanation`, `match_reasons`, `intent`, `ai_used`, and
  `fallback_used`.
- Anonymous and authenticated requests use separate throttle buckets.

The global `AI_FEATURES_ENABLED` switch and the cached
`feature.ai_search.enabled` `SiteSetting` must both be enabled. Disabled flags, provider errors,
invalid/non-finite vectors, SQLite, a missing vector extension, or an empty index degrade to
keyword search without exposing non-public products.

## Embedding indexing

The configured multilingual model is `gemini-embedding-2` with 1,536 dimensions. Vietnamese is
the primary index language. Vectors are stored in PostgreSQL `pgvector` and searched through an
HNSW cosine index. `AI_EMBEDDING_MODALITY=text` is intentionally explicit: approved products are
indexed from normalized title, description, category, brand, attributes, and curated image
`alt_text`. The current provider does **not** embed image pixels, so the system never claims true
multimodal similarity. A future multimodal provider can change the modality after a full re-index.

A SHA-256 content hash skips unchanged content; a successful re-index removes older embeddings
for that product/model. Product, category, brand, attribute, and media/alt-text changes enqueue an
immediate re-index after transaction commit. Price and stock remain live SQL filters/ranking data
and are deliberately not copied into embeddings, so a price update does not require re-indexing.
Celery Beat also queues a full reconciliation every 24 hours for missed events.

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

## Recommendation and similar-products ranking

Personalization has two independent inputs:

- The real-time layer weights the current product `4x`, cart products `3x`, the five most recent
  browsing products `2x`, then older browsing and wishlist products `1x`.
- The nightly batch layer builds `purchase-cooccurrence-v1` profiles from verified order items.
  It persists weighted category/brand preferences and products co-purchased by similar users.

Cold-start ranking uses the landing/traffic context, current season, and only demographics the
customer explicitly supplied. It then fills from in-stock popularity. The recommendation query
accepts optional `cart_products`, `landing_context`, and `traffic_source`; existing callers remain
compatible.

Every response includes a new `recommendation_id`. The storefront records impressions, clicks,
and add-to-cart actions at `POST /api/v1/ai/recommendation-events/`. Clients cannot submit a
purchase event; checkout asynchronously attributes actual `OrderItem` rows to recent interactions.
These events form the feedback dataset for future offline evaluation/retraining.

Similar products use the same content embeddings but enforce
`AI_SIMILAR_MIN_COSINE_SIMILARITY=0.45`. When vectors are unavailable, fallback candidates must at
least share the category (and prefer the same brand); unrelated global best sellers are not used.

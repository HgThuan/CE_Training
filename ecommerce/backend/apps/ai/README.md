# AI app

`apps.ai` is the provider-neutral boundary for smart search, semantic search, embeddings, and
future recommendation features. Callers use `AIService`; views, tasks, and domain services never
import a provider implementation directly.

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

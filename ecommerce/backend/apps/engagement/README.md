# Engagement app

`apps.engagement` owns customer interactions that are not part of the product catalog core:
product Q&A, wishlist membership, and shop follows.

## Q&A boundaries

- Anyone may list visible questions for a publicly available product.
- Only an active, non-deleted Customer may ask a question.
- Only the active Seller who owns the product's shop may answer.
- A question has at most one answer. Answer creation locks the question row and the database
  one-to-one constraint protects concurrent requests.
- Public author payloads expose only `id`, `full_name`, and `avatar_url`.

## Wishlist and follow boundaries

- Wishlist and follow endpoints accept only an authenticated, active, non-deleted Customer.
- Wishlist GET is always scoped from `request.user`; clients cannot provide a wishlist/user ID.
- Only public products and approved shops with active owners can be toggled or returned.
- Toggle services lock the Customer row. Follow also locks the Shop row; unique constraints are
  the final protection against duplicate rows.
- `price_when_added` is a nullable, non-negative snapshot of the product minimum price.
- Public shop responses expose aggregate follower state only, never follower identities or
  seller email/lock metadata.

All writes go through service classes; views are responsible for transport, permission classes,
strict input validation, and response formatting.

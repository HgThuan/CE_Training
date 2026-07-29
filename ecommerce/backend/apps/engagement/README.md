# Engagement app

`apps.engagement` owns customer interactions that are not part of the product catalog core.
Sprint 05 introduces product Q&A here; wishlist and shop-follow capabilities are added in the
following slice.

## Q&A boundaries

- Anyone may list visible questions for a publicly available product.
- Only an active, non-deleted Customer may ask a question.
- Only the active Seller who owns the product's shop may answer.
- A question has at most one answer. Answer creation locks the question row and the database
  one-to-one constraint protects concurrent requests.
- Public author payloads expose only `id`, `full_name`, and `avatar_url`.

All writes go through `QuestionService` or `AnswerService`; views are responsible for transport,
permission classes, validation, and response formatting.

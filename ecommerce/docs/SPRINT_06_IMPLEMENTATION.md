# Sprint 06 — Cart, Voucher & Flash Sale core

Requirement coverage: CUS-13, ADM-19, ADM-20, SEL-12, NFR-05, NFR-14.

## Resolved design points

- Use the official ERD names `Voucher` and `VoucherUsage`.
- Stack at most one platform voucher plus one shop voucher for each simulated
  `ShopOrder`. Shop discount is applied first, then the platform discount.
- Determine active Flash Sales at query/calculation time. This is simpler and
  less failure-prone than a scheduler for a two-day sprint, while timestamps
  remain the source of truth.
- Use the Flash Sale price as the base item price before voucher calculation.

## Explicit exclusions

No Sprint 06 model, API, service, route, or UI is provided for BON-03
(bundle/combo), BON-04 (add-on deal), or BON-14 (Flash Sale WebSocket).

## Guest-cart boundary

The guest cart is held entirely in browser localStorage. After authentication,
the frontend sends `{variant_id, quantity}` items to `/api/v1/cart/merge`. The
backend validates and merges them in one transaction.

The frontend keeps the required guest record minimal (`variant_id`, `quantity`,
`added_at`) and may cache product display fields. Cached fields are never trusted
for server-side pricing or availability. Items that cannot be revalidated remain
visible as unavailable so the customer can remove them explicitly.

## Frontend contract decisions

- Frontend request and response types mirror the implemented DRF serializers.
- Voucher preview sends structured platform and per-shop code lists so the
  one-platform-plus-one-shop stacking rule is unambiguous.
- Flash Sale countdowns use the server-provided timestamps. Live stock progress
  and WebSocket updates remain excluded from this sprint.

## Sprint 07 integration contract

Checkout may reuse `PromotionCalculationService.calculate` for a dry-run and
then explicitly call:

- `VoucherService.validate_and_apply(..., commit=True, order_reference=...)`;
- `FlashSaleService.reserve_flash_sale_quota(...)`;
- the inventory reservation service.

These writes must remain in the Sprint 07 checkout transaction boundary.

# Promotion module — Sprint 06 (ADM-19, ADM-20, SEL-12)

## Decisions

1. The domain names are `Voucher` and `VoucherUsage`.
2. Each simulated shop order accepts at most one platform voucher and one voucher
   owned by that shop. The limits are named constants in `services.py`.
3. Flash Sale activity is evaluated from database timestamps when queried. This
   avoids a scheduler and still restores the ordinary price immediately outside
   the active window.
4. An active Flash Sale price becomes the item base price; vouchers are applied
   afterward.

Bundle/combo, add-on deals, and WebSocket Flash Sale updates are intentionally
outside this module and Sprint 06.

## Services and concurrency

- `VoucherService.validate_and_apply(..., commit=False)` is a dry-run.
- With `commit=True`, it locks the voucher row and creates a unique
  `VoucherUsage` using the checkout `order_reference`.
- `FlashSaleService.reserve_flash_sale_quota` locks the sale item and updates
  `sold_count` with an `F()` expression.
- `PromotionCalculationService.calculate` is side-effect-free and returns a
  per-shop breakdown.

Concurrency tests use `TransactionTestCase` and real threads on PostgreSQL.
They are skipped on SQLite because SQLite does not implement the required
row-lock semantics.

## API

| Method | Path | Role |
|---|---|---|
| GET/POST | `/api/v1/admin/vouchers` | Admin, platform vouchers |
| GET/PATCH/DELETE | `/api/v1/admin/vouchers/{id}` | Admin |
| GET/POST | `/api/v1/seller/vouchers` | Seller, own shop |
| GET/PATCH/DELETE | `/api/v1/seller/vouchers/{id}` | Seller, own shop |
| GET | `/api/v1/customer/vouchers/available` | Customer |
| GET/POST | `/api/v1/admin/flash-sales` | Admin |
| GET/PATCH/DELETE | `/api/v1/admin/flash-sales/{id}` | Admin |
| GET | `/api/v1/flash-sales/active` | Public |

All list endpoints use the project `StandardPagination` response and use
`select_related`/`prefetch_related` for related display data.

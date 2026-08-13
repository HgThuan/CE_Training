# Promotion — campaign → collect → apply

Voucher codes are a secondary/private-code entry point. The normal lifecycle is:

1. Admin or Seller publishes a `voucher_campaign`.
2. Customer collects it atomically into `user_voucher`.
3. Checkout lists owned vouchers with eligibility reasons and a best-voucher suggestion.
4. Apply changes ownership to `pending_use` for 15 minutes.
5. The future Order transaction calls `UserVoucherService.mark_used`; cancellation or
   payment failure calls `UserVoucherService.rollback`.

The repository does not yet contain an Order/Payment aggregate, so this module does
not create a fake order or payment endpoint. The two lifecycle hooks above are the
integration boundary for that sprint.

## Concurrency and audit

- Collect locks the campaign row with `SELECT ... FOR UPDATE`, checks per-user and
  remaining limits, decrements `remaining_quantity`, and creates ownership in one
  transaction.
- `Idempotency-Key` is unique per customer, so retries cannot issue twice.
- Apply locks ownership rows; a voucher cannot be held by another checkout token.
- `VoucherEvent` records collect, apply, use, rollback, and expire operations.
- Run `python manage.py expire_vouchers` from cron to expire saved vouchers and
  release abandoned pending locks.

## Customer API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/voucher-center` | Collectable campaigns |
| POST | `/api/v1/vouchers/{campaignId}/collect` | Atomic/idempotent collect |
| GET | `/api/v1/me/vouchers?status=saved` | Owned voucher wallet/history |
| GET | `/api/v1/checkout/available-vouchers` | Eligibility and best voucher |
| POST | `/api/v1/checkout/apply-voucher` | Reprice and lock owned vouchers |
| POST | `/api/v1/checkout/apply-voucher-by-code` | Secondary private-code flow |
| GET | `/api/v1/shops/{shopId}/vouchers` | Public shop voucher badges |

Flash Sale remains side-effect-free during preview. Inventory, Flash Sale quota,
voucher use, and order creation must later commit in one Order transaction.

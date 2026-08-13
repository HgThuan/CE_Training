# Cart module — Sprint 06 (CUS-13)

## Design

- `Cart` belongs one-to-one to an authenticated `CustomerProfile`.
- Guest carts remain in frontend `localStorage`; the merge endpoint accepts an
  `items` payload after login. No anonymous cart/session row is created.
- `CartItem.unit_price_snapshot` records the price seen when an item is first
  added. A cart read compares it with the current price and reports
  `price_changed`.
- Cart quantities are validated against `InventoryBalance.available_stock`.
  Adding to a cart does not reserve inventory.

## Service

`CartService` owns add, update, localStorage merge, grouped summary, and checkout
preview. `preview_checkout` delegates to the promotion calculation service and
has no database side effects.

## API

All endpoints require a Customer JWT and use the common response envelope.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/cart/` | Cart grouped by shop |
| POST | `/api/v1/cart/items` | Add/increment item |
| PATCH | `/api/v1/cart/items/{id}` | Change quantity/selection |
| DELETE | `/api/v1/cart/items/{id}` | Remove item |
| POST | `/api/v1/cart/merge` | Merge localStorage items |
| POST | `/api/v1/cart/preview` | Dry-run pricing |

The summary exposes current stock, `is_valid`, `price_changed`, snapshot/current
prices, and selected subtotals.

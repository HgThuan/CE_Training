# Account app

This app owns the custom `User`, `AdminProfile`, `SellerProfile`, `CustomerProfile`,
email verification, password recovery, JWT rotation/blacklisting and role permissions.

Business actions live in `services.py`; views only validate, authorize and shape responses.
Refresh tokens use an HttpOnly cookie while access tokens are returned in the response body.
Security-sensitive changes increment `User.token_version` and blacklist outstanding refresh
tokens so existing sessions stop working immediately.

## Group 1 account management

- `CUS-05`: owner profile update, password change and validated avatar upload. Avatar files are
  re-encoded as JPEG and resized to at most 512 px before storage.
- `CUS-06`: owner-scoped address CRUD, soft delete and a conditional unique constraint for the
  active default address. Address APIs require the Customer role.
- `ADM-04`: searchable, filterable and paginated customer CRUD. Delete is a soft delete and
  immediately revokes authentication sessions.
- `ADM-06`: Admin lock/unlock with a required reason, audit entry, session revocation and an
  asynchronous status email.
- `ADM-07`: Admin-forced password reset invalidates the old password and all sessions, then sends
  a signed reset link asynchronously.

Admin operations protect the current Admin and Superuser accounts from self-lock/reset actions.

## Sprint 2 seller lifecycle

- `SellerOnboardingService` owns application submission, approval/rejection, role transition,
  Shop creation, notification, audit and post-commit Celery email scheduling.
- `SellerDocumentService` owns per-document verification and derives the aggregate profile
  verification status.
- `ShopService` owns owner updates, Admin edits, lock/unlock and seller soft deletion.
- `ShopService.update_shop_image` validates real image content, applies EXIF orientation, center
  crops and writes a fixed `512×512` logo or `1600×480` cover as WebP.
- `ShopBusinessPolicy` is the single contract that Product/Order create services must call; a
  locked/deleted shop cannot create new resources.
- `selectors.py` scopes Seller queries by authenticated user before resolving object IDs.
- `IsShopOwner` provides object-level enforcement. The permission test changes the URL from
  Seller A's Shop ID to Seller B's and expects 404 for both GET and PATCH.

Models introduced/expanded: `SellerProfile`, `SellerDocument`, `Shop`, `Notification`; the shared
`AuditLog` gains `reason` and `request_id`. Reusing the generic audit table avoids a duplicate
`AdminActionLog` while preserving the required actor/action/target/reason/timestamp fields.

Seller document content is MIME/content validated, stored under `media/private/` with randomized
names and never exposed through the public `/media/` Nginx location. Authorized application
responses contain a signed, expiring `/protected-media/` download URL.

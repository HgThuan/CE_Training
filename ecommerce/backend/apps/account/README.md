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

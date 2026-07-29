# Storefront

`storefront` owns homepage aggregation and Banner administration.

- Public: `GET /api/v1/home/`
- Admin: CRUD and reorder under `/api/v1/admin/banners/`
- Banner images are stored as validated public URLs. File upload is deferred until a shared
  object-storage contract is available.

Write operations go through `BannerService`; public reads go through selectors.

# Verified navigation routes

Route audit performed on 2026-09-02 against each owner repository's `main` branch.

| Destination | Repository | Verified commit | Registered entry route |
| --- | --- | --- | --- |
| Rooms | `NikaSir/ha-nikas-rooms` | `5afdfe7eac68168918877481254390be8cee33e2` | `/dashboard-rooms-v11/rooms` |
| Access | `NikaSir/ha-nikas-access` | `b57d40de6ef1b2d044f183ff7ce673c03d8df2b7` | `/dashboard-access-v1/home` |
| LIDER | `NikaSir/ha-lider-voltage-control` | `e32cc2a226b3f14ae36d8f7a4acf4689602d3303` | `/dashboard-lider` |
| Keenetic Hero 4G+ | `NikaSir/ha-keenetic-hero-4g` | `0c0ea3508dbc1053f241438ad9b8d975fd062d92` | `/dashboard-keenetic` |
| ZONT | `NikaSir/ha-zont` | `f4bb6d2fcca38a398739bca87e86c69cebcd67e1` | `/dashboard-zont` |

The unchanged base links `/dashboard-actions/home` and
`/dashboard-infrastructure/overview` remain external. The dedicated House route is
owned here at `/dashboard-house-v13/home`.

This audit verifies the outbound entry routes only. Updating each destination's
accepted return route from its current v11/v12 value to v13 is intentionally deferred
until the parallel House panel passes phone acceptance.

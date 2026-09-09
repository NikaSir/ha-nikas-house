# House panel compliance

Scope: the autonomous main House panel at the dedicated parallel route
`/dashboard-house-v13/home`. The existing `/dashboard-house-v12/home` owner is preserved.

| Requirement | Status |
|---|---|
| NikaS UI Standard 2.2 / Navigation 1.2 documents and hashes | PASS |
| One integration-owned route | PASS |
| Existing YAML routes preserved | PASS |
| Header and Bottom Tab Bar outside the work canvas | PASS |
| One work canvas | PASS |
| Explicit Home Assistant navigation; no browser-history Back | PASS |
| Unknown and unavailable remain explicit | PASS |
| Missing/private inventory preserves route with fail-closed content | PASS — unit/static evidence; live HA retry acceptance remains GAP |
| Refresh is read-only, single-flight and does not reload the page | PASS — production regression; browser animation remains GAP |
| Host-bound 60/64 px shell, 26 px Bottom Tab Bar icons and boundary guard | PASS — static/production checks; viewport matrix remains GAP |
| No connection plaque on `Дом сейчас` | PASS |
| Autonomous packaged frontend bundle | PASS |
| No Infrastructure, Actions, Rooms or generated-panel runtime | PASS |
| Destination-panel return allowlists switched to v13 | PASS for migrated owners; remaining repositories are tracked separately |
| House publication through `main`, without GitHub Releases | PASS — approved repository policy; target HACS delivery acceptance remains GAP |
| Target-phone visual and lifecycle acceptance | GAP |

Detailed panels are evaluated in their own repositories and are outside this compliance record.

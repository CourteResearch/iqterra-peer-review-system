# Integration architecture

```text
Moodle tenant
  | LTI 1.3 launch / NRPS roster / AGS score passback
  v
LTI gateway (Hono + lti-tool toolkit)
  | tenant-scoped internal API
  v
IQTerra peer-review service
  |-- allocation engine
  |-- rubric and weighting model
  |-- reviewer UI (Astro)
  |-- moderation and flags
  |-- audit log
  v
PostgreSQL (tenant_id on every business table)
```

## Boundary rule

Moodle receives only the integration data it needs: launch context, roster-derived identities, activity references, and final scores. Allocation constraints, rubric weightings, reviewer assignments, moderation decisions, and audit records remain in IQTerra storage.

## LTI integration seam

The starter service currently exposes health and allocation-preview endpoints. The next step is to install `@lti-tool/core`, `@lti-tool/hono`, and a production storage adapter, then mount the toolkit's `/lti/login`, `/lti/launch`, and `/lti/jwks` routes. Keep the LTI adapter separate from domain services so Moodle-specific claims do not leak into allocation logic.

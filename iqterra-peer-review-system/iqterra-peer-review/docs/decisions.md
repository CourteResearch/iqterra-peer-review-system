# Development decisions

## Use the LTI toolkit as an adapter, not as the domain model

Moodle integration changes are isolated in `apps/lti-service`. Allocation, rubric, moderation, and tenant rules remain ordinary domain services so they can be tested without a live Moodle instance.

## Use a deterministic allocation seed

A seed makes demonstrations reproducible while still allowing a new allocation run. Store the seed, algorithm version, requester, and timestamp in the audit log when persistence is added.

## Keep the first UI intentionally small

The Astro screen is a visual shell for the reviewer workflow. The next implementation step is to replace placeholder content with authenticated, tenant-scoped API calls rather than prematurely building a large frontend.

# Roadmap

## Milestone 1 — foundation (this repository)

- [x] TypeScript workspace
- [x] Deterministic allocation engine
- [x] No self-review and no reciprocal pair validation
- [x] Balanced-load test with an 11-person cohort
- [x] 50-person allocation test
- [x] Hono API seam
- [x] Astro reviewer UI shell
- [x] Architecture and evidence documentation

## Milestone 2 — LTI and persistence

- [ ] Configure Moodle sandbox as an LTI 1.3 platform
- [ ] Mount `@lti-tool/core` and `@lti-tool/hono`
- [ ] Add PostgreSQL schema with `tenant_id` on every table
- [ ] Persist clients, deployments, courses, activities, members, submissions, assignments, reviews, flags, and audit events
- [ ] Implement NRPS roster synchronisation
- [ ] Implement AGS line-item creation and score passback

## Milestone 3 — product workflow

- [ ] Add submission references without replacing Moodle submission storage
- [ ] Add rubric authoring and versioning
- [ ] Add reviewer queue and blind-review presentation
- [ ] Add moderation dashboard, flags, and resolution history
- [ ] Add tenant administrator settings

## Milestone 4 — proof

- [ ] Run the full Moodle sandbox flow: launch → roster → submit → allocate → review → moderate → passback
- [ ] Run isolation tests attempting cross-tenant reads and writes
- [ ] Run allocation evidence for 50+ synthetic users
- [ ] Capture screenshots, logs, test output, and a deployment runbook

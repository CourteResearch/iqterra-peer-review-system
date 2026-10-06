# IQTerra Moodle Peer-Review Platform

A coursework starter for **ICT801A / CYB805A / DAT805A — IQT-02**. It is deliberately a foundation, not a completed submission.

## What works now

- Deterministic, constraint-aware allocation engine
- No self-review and no reciprocal pairs
- Balanced reviewer loads where the requested allocation is feasible
- Automated 50-student test
- Hono service with allocation preview endpoint
- Astro reviewer interface shell
- Architecture, roadmap, and assessment evidence plan

## Quick start

```bash
npm install
npm test
npm run typecheck
npm run dev:lti
# in another terminal: npm run dev:ui
```

Then visit `http://localhost:4321` for the UI and `http://localhost:8787/health` for the service. Preview an allocation with:

```bash
curl -X POST http://localhost:8787/api/allocations/preview \\
  -H 'content-type: application/json' \\
  -d '{"students":[{"id":"a"},{"id":"b"},{"id":"c"},{"id":"d"}],"reviewsPerSubmission":1,"seed":42}'
```

## Important project boundary

The original [`lti-tool/lti-tool`](https://github.com/lti-tool/lti-tool) project is an LTI 1.3 toolkit. This repository is the application layer around that idea. Before presenting this as a completed project, implement the LTI routes, persistence, rubric workflow, moderation, tenant isolation, and Moodle sandbox evidence described in [`docs/roadmap.md`](./docs/roadmap.md).

## Suggested team split

1. **LTI/integration:** Moodle registration, launch, NRPS, AGS, key management.
2. **Domain/data:** PostgreSQL schema, tenant authorization, rubric versioning, audit log.
3. **Allocation:** constraints, algorithm proof, performance tests, failure handling.
4. **Product:** Astro reviewer and moderator interfaces, blind-review UX.
5. **Evidence/DevOps:** deployment, test fixtures, runbook, screenshots, demo script.

## License and attribution

Add the MIT attribution for any reused `lti-tool` code or package. Record the exact upstream version and your own changes in the final report.

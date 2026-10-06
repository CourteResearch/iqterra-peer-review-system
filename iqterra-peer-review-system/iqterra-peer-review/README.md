# IQTerra Moodle Peer-Review Platform


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



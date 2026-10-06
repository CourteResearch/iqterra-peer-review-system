import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import { z } from 'zod';
import { allocateReviews } from '../../../pkg/allocation/src/index.js';

const app = new Hono();

app.get('/health', (c) => c.json({ service: 'iqterra-peer-review', status: 'ok' }));

const allocationRequest = z.object({
  students: z.array(z.object({ id: z.string().min(1) })).min(3),
  reviewsPerSubmission: z.number().int().positive().default(2),
  seed: z.number().int().default(1),
});

app.post('/api/allocations/preview', async (c) => {
  const parsed = allocationRequest.safeParse(await c.req.json());
  if (!parsed.success) return c.json({ error: parsed.error.flatten() }, 400);
  try {
    return c.json({ allocation: allocateReviews(parsed.data.students, parsed.data) });
  } catch (error) {
    return c.json({ error: error instanceof Error ? error.message : 'Allocation failed' }, 422);
  }
});

// TODO: Connect these routes to @lti-tool/core and @lti-tool/hono:
// POST /lti/login, POST /lti/launch, GET /lti/jwks
// Then map NRPS members to tenant-scoped students and AGS scores to Moodle.

const port = Number(process.env.PORT ?? 8787);
serve({ fetch: app.fetch, port }, (info) => {
  console.log(`IQTerra LTI service listening on http://localhost:${info.port}`);
});

export default app;

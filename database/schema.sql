-- Illustrative tenant-scoped schema. Apply only to a development database.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issuer text NOT NULL,
  client_id text NOT NULL,
  deployment_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (issuer, client_id, deployment_id)
);

CREATE TABLE IF NOT EXISTS peer_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  reviewer_subject text NOT NULL,
  submission_ref text NOT NULL,
  comment_text text,
  status text NOT NULL DEFAULT 'allocated',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, reviewer_subject, submission_ref)
);

CREATE TABLE IF NOT EXISTS rubric_criteria (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  criterion_name text NOT NULL,
  description text NOT NULL,
  -- Never expose this field through student-facing API responses.
  weighting numeric(7,4) NOT NULL CHECK (weighting >= 0 AND weighting <= 1),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
  id bigserial PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  actor_subject text NOT NULL,
  action text NOT NULL,
  object_ref text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE peer_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY peer_reviews_tenant_isolation ON peer_reviews
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE rubric_criteria ENABLE ROW LEVEL SECURITY;
ALTER TABLE rubric_criteria FORCE ROW LEVEL SECURITY;
CREATE POLICY rubric_criteria_tenant_isolation ON rubric_criteria
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_events_tenant_isolation ON audit_events
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

-- Important: application must set tenant context transaction-locally:
-- SELECT set_config('app.tenant_id', '<validated-tenant-uuid>', true);
-- The runtime DB role must not be a superuser and must not have BYPASSRLS.

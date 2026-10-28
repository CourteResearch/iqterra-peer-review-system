import { pgTable, pgEnum, varchar, integer, text, timestamp, boolean, jsonb } from 'drizzle-orm/pg-core';

// Enums
export const tenantRole = pgEnum('tenant_role', ['instructor', 'student']);

// Tenant table - root isolation boundary
export const tenants = pgTable('tenants', {
  id: varchar('id', { length: 256 }).primaryKey(),
  name: varchar('name', { length: 256 }).notNull(),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// User roles enum
export const userRole = pgEnum('user_role', ['student', 'reviewer', 'instructor', 'admin']);

// Courses table
export const courses = pgTable('courses', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  code: varchar('code', { length: 128 }).notNull,
  name: varchar('name', { length: 256 }).notNull,
  description: text('description'),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// Course memberships table
export const courseMemberships = pgTable('course_memberships', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  user_id: varchar('user_id', { length: 256 }).notNull().references(() => users.id),
  role: userRole('role').notNull,
  joined_at: timestamp('joined_at', { mode: 'string' }).defaultNow(),
  UNIQUE(course_id, user_id),
});

// Activities table
export const activities = pgTable('activities', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  title: varchar('title', { length: 256 }).notNull,
  description: text('description'),
  instructions: text('instructions'),
  max_score: integer('max_score').notNull.default(100),
  rubric_id: varchar('rubric_id', { length: 256 }),
  released: boolean('released').default(false),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// Submissions table - Moodle references, not files
export const submissions = pgTable('submissions', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  activity_id: varchar('activity_id', { length: 256 }).notNull().references(() => activities.id),
  user_id: varchar('user_id', { length: 256 }).notNull().references(() => users.id),
  moodle_submission_id: varchar('moodle_submission_id', { length: 128 }),
  moodle_file_url: varchar('moodle_file_url', { length: 512 }),
  submitted_at: timestamp('submitted_at', { mode: 'string' }),
  grade: integer('grade'),
  comment_count: integer('comment_count').default(0),
  status: varchar('status', { length: 50 }).default('pending'),
});

// Rubric versions table - versioned rubrics
export const rubricVersions = pgTable('rubric_versions', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).references(() => courses.id),
  name: varchar('name', { length: 256 }).notNull,
  description: text('description'),
  is_active: boolean('is_active').default(true),
  weight_source: text('weight_source').notNull,
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// Rubric questions/items within each version
export const rubricQuestions = pgTable('rubric_questions', {
  id: varchar('id', { length: 256 }).primaryKey(),
  rubric_version_id: varchar('rubric_version_id', { length: 256 }).notNull().references(() => rubricVersions.id),
  title: varchar('title', { length: 256 }).notNull,
  description: text('description'),
  scale_min: integer('scale_min').notNull.default(1),
  scale_max: integer('scale_max').notNull.default(5),
  weight: integer('weight').notNull,
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// Reviewer allocations table
export const allocations = pgTable('allocations', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  activity_id: varchar('activity_id', { length: 256 }).notNull().references(() => activities.id),
  reviewer_id: varchar('reviewer_id', { length: 256 }).notNull().references(() => users.id),
  reviewee_id: varchar('reviewee_id', { length: 256 }).notNull().references(() => users.id),
  status: varchar('status', { length: 50 }).default('pending'),
  allocated_at: timestamp('allocated_at', { mode: 'string' }).defaultNow(),
  UNIQUE(course_id, activity_id, reviewer_id),
});

// Reviews table - review responses including question-level answers
export const reviews = pgTable('reviews', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  activity_id: varchar('activity_id', { length: 256 }).notNull().references(() => activities.id),
  reviewer_id: varchar('reviewer_id', { length: 256 }).notNull().references(() => users.id),
  reviewee_id: varchar('reviewee_id', { length: 256 }).notNull().references(() => users.id),
  status: varchar('status', { length: 50 }).default('pending'),
  submitted_at: timestamp('submitted_at', { mode: 'string' }),
  overall_score: integer('overall_score'),
  answers: jsonb('answers').$type<{
    [questionId: string]: {
      score: number;
      comment: string;
    };
  }>.default({}),
  reviewer_blind: boolean('reviewer_blind').default(true),
  reviewee_blind: boolean('reviewee_blind').default(true),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
  updated_at: timestamp('updated_at', { mode: 'string' }).defaultNow(),
});

// Moderation flags/actions table
export const moderationFlags = pgTable('moderation_flags', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  activity_id: varchar('activity_id', { length: 256 }).notNull().references(() => activities.id),
  review_id: varchar('review_id', { length: 256 }).references(() => reviews.id),
  flag_type: varchar('flag_type', { length: 100 }).notNull,
  severity: varchar('severity', { length: 50 }).notNull.default('medium'),
  description: text('description'),
  resolved: boolean('resolved').default(false),
  resolved_by: varchar('resolved_by', { length: 256 }),
  resolved_at: timestamp('resolved_at', { mode: 'string' }),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// Grade passback delivery records
export const gradePassback = pgTable('grade_passback', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  course_id: varchar('course_id', { length: 256 }).notNull().references(() => courses.id),
  user_id: varchar('user_id', { length: 256 }).notNull().references(() => users.id),
  moodle_grade_item_id: varchar('moodle_grade_item_id', { length: 128 }),
  moodle_grade: integer('moodle_grade'),
  status: varchar('status', { length: 50 }).default('pending'),
  error_message: text('error_message'),
  sent_at: timestamp('sent_at', { mode: 'string' }),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});

// Audit events table - append-oriented
export const auditEvents = pgTable('audit_events', {
  id: varchar('id', { length: 256 }).primaryKey(),
  tenant_id: varchar('tenant_id', { length: 256 }).notNull().references(() => tenants.id),
  event_type: varchar('event_type', { length: 100 }).notNull,
  entity_type: varchar('entity_type', { length: 50 }),
  entity_id: varchar('entity_id', { length: 256 }),
  user_id: varchar('user_id', { length: 256 }),
  details: jsonb('details'),
  created_at: timestamp('created_at', { mode: 'string' }).defaultNow(),
});
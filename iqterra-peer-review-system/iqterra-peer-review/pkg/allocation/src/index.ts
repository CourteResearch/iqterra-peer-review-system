export type Student = { id: string };

export type Allocation = {
  submissionId: string;
  reviewerId: string;
}[];

export type AllocationOptions = {
  reviewsPerSubmission?: number;
  seed?: number;
  maxSearchNodes?: number;
};

export class AllocationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AllocationError';
  }
}

function hash(value: string, seed: number): number {
  let h = (2166136261 ^ seed) >>> 0;
  for (const char of value) {
    h ^= char.charCodeAt(0);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/**
 * Allocates each student's submission to distinct reviewers.
 * Constraints: no self-review, no reciprocal pair, and load difference <= 1
 * whenever a solution satisfying the requested degree exists.
 */
export function allocateReviews(
  students: Student[],
  options: AllocationOptions = {},
): Allocation {
  const reviewsPerSubmission = options.reviewsPerSubmission ?? 2;
  const seed = options.seed ?? 1;
  const maxSearchNodes = options.maxSearchNodes ?? 250_000;

  if (students.length < 3) {
    throw new AllocationError('At least three students are required.');
  }
  if (!Number.isInteger(reviewsPerSubmission) || reviewsPerSubmission < 1) {
    throw new AllocationError('reviewsPerSubmission must be a positive integer.');
  }
  if (reviewsPerSubmission >= students.length - 1) {
    throw new AllocationError('Not enough eligible reviewers for the requested degree.');
  }
  const ids = students.map((student) => student.id);
  if (new Set(ids).size !== ids.length || ids.some((id) => id.length === 0)) {
    throw new AllocationError('Student IDs must be unique and non-empty.');
  }

  const loads = new Map(ids.map((id) => [id, 0]));
  const assigned = new Map<string, Set<string>>();
  const result: Allocation = [];
  let searchNodes = 0;

  // Allocate the most constrained submissions first. This also makes failure
  // happen early instead of producing a partial, misleading allocation.
  const submissionOrder = [...ids].sort(
    (a, b) => hash(a, seed) - hash(b, seed),
  );

  const canReview = (reviewer: string, submission: string): boolean => {
    if (reviewer === submission) return false;
    if (assigned.get(submission)?.has(reviewer)) return false;
    // If submission already reviews reviewer, the pair would be reciprocal.
    if (assigned.get(reviewer)?.has(submission)) return false;
    return true;
  };

  const chooseReviewers = (submission: string, chosen: string[]): boolean => {
    if (chosen.length === reviewsPerSubmission) return true;
    searchNodes += 1;
    if (searchNodes > maxSearchNodes) return false;

    const candidates = ids
      .filter((reviewer) => !chosen.includes(reviewer) && canReview(reviewer, submission))
      .sort((a, b) => {
        const loadDiff = (loads.get(a) ?? 0) - (loads.get(b) ?? 0);
        return loadDiff || hash(`${submission}:${a}`, seed) - hash(`${submission}:${b}`, seed);
      });

    for (const reviewer of candidates) {
      // Never allow a reviewer to get more than one assignment above the
      // current minimum load; this is the balancing invariant.
      const minLoad = Math.min(...loads.values());
      if ((loads.get(reviewer) ?? 0) > minLoad + 1) continue;
      chosen.push(reviewer);
      (assigned.get(submission) ?? assigned.set(submission, new Set()).get(submission)!).add(reviewer);
      loads.set(reviewer, (loads.get(reviewer) ?? 0) + 1);
      if (chooseReviewers(submission, chosen)) return true;
      loads.set(reviewer, (loads.get(reviewer) ?? 0) - 1);
      assigned.get(submission)?.delete(reviewer);
      chosen.pop();
    }
    return false;
  };

  for (const submission of submissionOrder) {
    if (!chooseReviewers(submission, [])) {
      throw new AllocationError(
        `Could not satisfy allocation constraints after ${searchNodes} search nodes.`,
      );
    }
    for (const reviewer of assigned.get(submission) ?? []) {
      result.push({ submissionId: submission, reviewerId: reviewer });
    }
  }

  return result.sort((a, b) =>
    a.submissionId.localeCompare(b.submissionId) || a.reviewerId.localeCompare(b.reviewerId),
  );
}

export function validateAllocation(
  students: Student[],
  allocation: Allocation,
  reviewsPerSubmission: number,
): string[] {
  const errors: string[] = [];
  const ids = new Set(students.map((student) => student.id));
  const bySubmission = new Map<string, string[]>();
  const pairs = new Set<string>();
  for (const { submissionId, reviewerId } of allocation) {
    if (!ids.has(submissionId) || !ids.has(reviewerId)) errors.push('Unknown student ID.');
    if (submissionId === reviewerId) errors.push(`Self-review: ${submissionId}.`);
    const key = `${submissionId}->${reviewerId}`;
    if (pairs.has(key)) errors.push(`Duplicate assignment: ${key}.`);
    pairs.add(key);
    bySubmission.set(submissionId, [...(bySubmission.get(submissionId) ?? []), reviewerId]);
    if (pairs.has(`${reviewerId}->${submissionId}`)) errors.push(`Reciprocal pair: ${submissionId}/${reviewerId}.`);
  }
  for (const id of ids) {
    if ((bySubmission.get(id) ?? []).length !== reviewsPerSubmission) {
      errors.push(`${id} has the wrong number of reviewers.`);
    }
  }
  return errors;
}

import { describe, expect, it } from 'vitest';
import { AllocationError, allocateReviews, validateAllocation } from '../src/index.js';

const cohort = (size: number) => Array.from({ length: size }, (_, i) => ({ id: `student-${i + 1}` }));

describe('allocateReviews', () => {
  it('allocates a 50-student cohort with no self-review or reciprocal pairs', () => {
    const students = cohort(50);
    const allocation = allocateReviews(students, { reviewsPerSubmission: 2, seed: 42 });
    expect(allocation).toHaveLength(100);
    expect(validateAllocation(students, allocation, 2)).toEqual([]);
  });

  it('keeps reviewer loads balanced', () => {
    const students = cohort(11);
    const allocation = allocateReviews(students, { reviewsPerSubmission: 2, seed: 7 });
    const loads = students.map(({ id }) => allocation.filter((a) => a.reviewerId === id).length);
    expect(Math.max(...loads) - Math.min(...loads)).toBeLessThanOrEqual(1);
  });

  it('is deterministic for the same seed', () => {
    const students = cohort(12);
    expect(allocateReviews(students, { seed: 99 })).toEqual(allocateReviews(students, { seed: 99 }));
  });

  it('rejects an impossible cohort', () => {
    expect(() => allocateReviews(cohort(3), { reviewsPerSubmission: 2 })).toThrow(AllocationError);
  });
});

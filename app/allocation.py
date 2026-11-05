"""Pure allocation engine for synthetic peer-review assignments.

Each student reviews k other students. No self-allocation and no reciprocal
reviewer/submission pair are permitted. The algorithm is deterministic for
reproducible tests and balances reviewer loads as evenly as possible.
"""

from collections import Counter
from typing import Sequence


def allocate_reviews(
    student_ids: Sequence[str], reviewers_per_submission: int = 3
) -> list[tuple[str, str]]:
    students = list(student_ids)
    if len(students) != len(set(students)):
        raise ValueError("student_ids must be unique")
    n = len(students)
    if n < 3:
        raise ValueError("At least 3 students are required")
    if reviewers_per_submission < 1 or reviewers_per_submission >= n:
        raise ValueError("reviewers_per_submission must be between 1 and n-1")

    # A directed circular graph is regular whenever k is strictly less than
    # half the cohort size; offsets 1..k guarantee balanced loads and avoid
    # reciprocal edges. Use the greedy fallback for denser graphs.
    if 2 * reviewers_per_submission < n:
        return [
            (students[(i + offset) % n], students[i])
            for i in range(n)
            for offset in range(1, reviewers_per_submission + 1)
        ]
    assignments: list[tuple[str, str]] = []
    pairs: set[tuple[str, str]] = set()
    loads = Counter({s: 0 for s in students})
    target_index = {s: i for i, s in enumerate(students)}

    for submission in students:
        sub_i = target_index[submission]
        selected = []
        candidates = sorted(
            (s for s in students if s != submission),
            key=lambda s: (loads[s], (target_index[s] - sub_i) % n, target_index[s]),
        )
        for reviewer in candidates:
            if len(selected) >= reviewers_per_submission:
                break
            if (submission, reviewer) in pairs:
                continue  # would create reviewer->submission and reverse
            selected.append(reviewer)
            pairs.add((reviewer, submission))
            loads[reviewer] += 1
        if len(selected) != reviewers_per_submission:
            raise ValueError(
                "Could not satisfy constraints for this cohort and review count; "
                "use a graph-search/optimisation allocator for this configuration."
            )
        assignments.extend((reviewer, submission) for reviewer in selected)

    # Final invariant checks: these are deliberately retained server-side.
    for reviewer, submission in assignments:
        if reviewer == submission:
            raise AssertionError("Self-allocation detected")
        if (submission, reviewer) in pairs:
            raise AssertionError("Reciprocal pair detected")
    return assignments

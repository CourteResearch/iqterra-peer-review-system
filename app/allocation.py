"""Pure allocation engine for synthetic peer-review assignments.

Each student reviews k other students. Self-allocation is never permitted.
Reciprocal reviews are avoided except when a two-student cohort has no
alternative. The algorithm is deterministic for reproducible tests and balances
reviewer loads as evenly as possible.
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
    if n < 2:
        raise ValueError("At least 2 students with submitted work are required")
    if reviewers_per_submission < 1 or reviewers_per_submission >= n:
        raise ValueError("reviewers_per_submission must be between 1 and n-1")
    if n == 2:
        return [(students[1], students[0]), (students[0], students[1])]

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


def allocate_group_reviews(
    reviewer_ids: Sequence[str],
    submissions: Sequence[tuple[str, int]],
    reviewers_per_submission: int,
) -> list[tuple[str, int]]:
    """Allocate individual submissions to their group peers.

    Reviewer IDs come from active group membership, while target owners come
    from students who submitted. This allows group members to review even if
    they have not submitted their own work.
    """
    reviewers = list(reviewer_ids)
    if len(reviewers) != len(set(reviewers)):
        raise ValueError("reviewer_ids must be unique")
    if not submissions:
        raise ValueError("At least one submission is required")
    if reviewers_per_submission < 1:
        raise ValueError("reviewers_per_submission must be at least 1")
    if len({submission_id for _, submission_id in submissions}) != len(submissions):
        raise ValueError("submission IDs must be unique")
    if len({owner_id for owner_id, _ in submissions}) != len(submissions):
        raise ValueError("Each student can have only one submission per assignment")
    reviewer_set = set(reviewers)
    if any(owner_id not in reviewer_set for owner_id, _ in submissions):
        raise ValueError("Every submission owner must be a member of its review group")
    if any(len(reviewer_set - {owner_id}) < reviewers_per_submission for owner_id, _ in submissions):
        raise ValueError(
            "Each submission needs enough other group members to meet the reviewer count"
        )

    reviewer_order = {reviewer_id: i for i, reviewer_id in enumerate(reviewers)}
    loads = Counter({reviewer_id: 0 for reviewer_id in reviewers})
    assigned: list[tuple[str, int]] = []
    reviewers_by_owner: dict[str, set[str]] = {}
    owner_by_submission = {
        submission_id: owner_id for owner_id, submission_id in submissions
    }

    for owner_id, submission_id in submissions:
        selected: list[str] = []
        for _ in range(reviewers_per_submission):
            candidates = [
                reviewer_id
                for reviewer_id in reviewers
                if reviewer_id != owner_id and reviewer_id not in selected
            ]
            candidates.sort(
                key=lambda reviewer_id: (
                    loads[reviewer_id],
                    owner_id in reviewers_by_owner.get(reviewer_id, set()),
                    reviewer_order[reviewer_id],
                )
            )
            if not candidates:
                raise ValueError("Could not find enough eligible group reviewers")
            reviewer_id = candidates[0]
            selected.append(reviewer_id)
            loads[reviewer_id] += 1
            assigned.append((reviewer_id, submission_id))
            reviewers_by_owner.setdefault(owner_id, set()).add(reviewer_id)

    return assigned

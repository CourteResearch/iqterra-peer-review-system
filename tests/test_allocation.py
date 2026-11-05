from app.allocation import allocate_group_reviews, allocate_reviews


def test_no_self_allocation_or_reciprocal_pairs():
    students = [f"s{i}" for i in range(50)]
    assignments = allocate_reviews(students, 3)
    pairs = set(assignments)
    assert len(assignments) == 150
    assert all(reviewer != submission for reviewer, submission in assignments)
    assert all(
        (submission, reviewer) not in pairs for reviewer, submission in assignments
    )


def test_balanced_loads():
    students = [f"s{i}" for i in range(50)]
    assignments = allocate_reviews(students, 3)
    loads = {s: 0 for s in students}
    for reviewer, _ in assignments:
        loads[reviewer] += 1
    assert max(loads.values()) - min(loads.values()) <= 1


def test_duplicate_students_rejected():
    try:
        allocate_reviews(["a", "a", "b"])
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_each_submission_receives_exactly_three_distinct_reviewers():
    students = [f"s{i}" for i in range(50)]
    assignments = allocate_reviews(students, 3)

    reviewers_by_submission = {student: [] for student in students}

    for reviewer, submission in assignments:
        reviewers_by_submission[submission].append(reviewer)

    for submission, reviewers in reviewers_by_submission.items():
        assert len(reviewers) == 3, f"{submission} should receive exactly 3 reviews"
        assert (
            len(set(reviewers)) == 3
        ), f"{submission} should have 3 distinct reviewers"


def test_two_students_receive_one_reciprocal_review_each():
    assignments = allocate_reviews(["a", "b"], 1)
    assert set(assignments) == {("a", "b"), ("b", "a")}


def test_one_student_rejected():
    try:
        allocate_reviews(["a"], 1)
    except ValueError as exc:
        assert "At least 2 students" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_invalid_review_count_rejected():
    students = ["a", "b", "c"]

    try:
        allocate_reviews(students, 3)
    except ValueError as exc:
        assert "reviewers_per_submission" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_group_members_can_review_without_submitting():
    allocations = allocate_group_reviews(
        ["s1", "s2", "s3", "s4"],
        [("s1", 101), ("s2", 102)],
        2,
    )
    assert len(allocations) == 4
    assert all(reviewer != ("s1" if submission == 101 else "s2")
               for reviewer, submission in allocations)
    assert {reviewer for reviewer, _ in allocations} <= {"s1", "s2", "s3", "s4"}
    assert any(reviewer in {"s3", "s4"} for reviewer, _ in allocations)


def test_group_allocation_rejects_missing_teammate_reviewers():
    try:
        allocate_group_reviews(["s1", "s2"], [("s1", 101)], 2)
    except ValueError as exc:
        assert "enough other group members" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

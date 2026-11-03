"""Small shared database response helpers."""


def questions(c, aid):
    return [
        dict(id=r["id"], prompt=r["prompt"], order=r["question_order"])
        for r in c.execute(
            "SELECT * FROM questions WHERE assignment_id=? ORDER BY question_order",
            (aid,),
        )
    ]

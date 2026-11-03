from fastapi.testclient import TestClient
from app.main import app, ASSETS_DIR


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").json() == {"status": "ok"}


def test_dashboard_served():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


def test_demo_allocator():
    with TestClient(app) as client:
        response = client.post("/api/demo/allocation")
        assert response.status_code == 200
        assert response.json()["assignment_count"] == 30
        assert len(response.json()["assignments"]) == 30
        assert (
            len({item["submission_id"] for item in response.json()["assignments"]})
            == 10
        )
        pairs = {
            (item["reviewer_id"], item["submission_id"])
            for item in response.json()["assignments"]
        }
        assert all(reviewer != submission for reviewer, submission in pairs)
        assert all(
            (submission, reviewer) not in pairs for reviewer, submission in pairs
        )
        assert (
            response.json()["review_load_max"] - response.json()["review_load_min"] <= 1
        )


def test_built_frontend_asset_is_served():
    if not ASSETS_DIR.is_dir():
        return
    assets = list(ASSETS_DIR.iterdir())
    assert assets, "frontend build asset directory is empty"
    with TestClient(app) as client:
        response = client.get(f"/assets/{assets[0].name}")
        assert response.status_code == 200
        assert response.content

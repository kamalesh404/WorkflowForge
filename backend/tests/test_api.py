import time

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_health():
    with _client() as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"


def test_create_workflow():
    payload = {
        "name": "api-basic",
        "description": "basic workflow",
        "tasks": [
            {"name": "t1", "dependencies": [], "params": {}},
        ],
    }
    with _client() as client:
        resp = client.post("/api/workflows", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "api-basic"
        assert len(body["tasks"]) == 1


def test_invalid_workflow_cycle_returns_400():
    payload = {
        "name": "api-cycle",
        "description": "",
        "tasks": [
            {"id": "a", "name": "a", "dependencies": ["c"]},
            {"id": "b", "name": "b", "dependencies": ["a"]},
            {"id": "c", "name": "c", "dependencies": ["b"]},
        ],
    }
    with _client() as client:
        resp = client.post("/api/workflows", json=payload)
        assert resp.status_code == 400


def test_execute_and_get_execution():
    payload = {
        "name": "api-exec",
        "description": "",
        "tasks": [
            {"name": "t1", "dependencies": []},
        ],
    }
    with _client() as client:
        created = client.post("/api/workflows", json=payload)
        assert created.status_code == 201
        workflow_id = created.json()["id"]
        executed = client.post(f"/api/workflows/{workflow_id}/execute")
        assert executed.status_code == 202
        execution_id = executed.json()["execution_id"]
        assert execution_id
        for _ in range(50):
            got = client.get(f"/api/executions/{execution_id}")
            assert got.status_code == 200
            if got.json()["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.1)
        final = client.get(f"/api/executions/{execution_id}")
        assert final.status_code == 200
        assert final.json()["id"] == execution_id


def test_metrics_endpoint():
    payload = {
        "name": "api-metrics",
        "description": "",
        "tasks": [
            {"name": "t1", "dependencies": []},
        ],
    }
    with _client() as client:
        created = client.post("/api/workflows", json=payload)
        assert created.status_code == 201
        workflow_id = created.json()["id"]
        resp = client.get(f"/api/workflows/{workflow_id}/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["workflow_id"] == workflow_id
        assert "total_executions" in body


def test_schedule_endpoint_validation():
    payload = {
        "name": "api-sched",
        "description": "",
        "tasks": [
            {"name": "t1", "dependencies": []},
        ],
    }
    with _client() as client:
        created = client.post("/api/workflows", json=payload)
        assert created.status_code == 201
        workflow_id = created.json()["id"]
        missing = client.post(f"/api/workflows/{workflow_id}/schedule", json={})
        assert missing.status_code == 400
        invalid = client.post(
            f"/api/workflows/{workflow_id}/schedule", json={"cron": "not-a-cron"}
        )
        assert invalid.status_code == 400
        valid = client.post(
            f"/api/workflows/{workflow_id}/schedule",
            json={"cron": "*/5 * * * *", "name": "every-five"},
        )
        assert valid.status_code == 201
        body = valid.json()
        assert body["scheduled"] is True
        assert "schedule_id" in body

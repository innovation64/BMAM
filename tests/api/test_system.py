"""Tests for /v1/system/* endpoints."""


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/v1/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["health_percentage"] == 100.0
        assert "features" in data


class TestStats:
    def test_system_stats(self, client):
        resp = client.get("/v1/system/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_memories"] == 42
        assert data["episodic_memories"] == 30
        assert data["semantic_memories"] == 12


class TestRoot:
    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "BMAM Memory Middleware"
        assert "docs" in data

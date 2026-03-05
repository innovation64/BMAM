"""Tests for /v1/memories/search/ endpoint."""


class TestSearch:
    def test_semantic_search(self, client):
        resp = client.post(
            "/v1/memories/search/",
            json={"query": "outdoor activities", "user_id": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["retrieval_mode"] == "semantic"
        assert data["total"] >= 1
        assert data["results"][0]["content"] == "I love hiking"

    def test_brain_distributed_search(self, client):
        resp = client.post(
            "/v1/memories/search/",
            json={
                "query": "outdoor activities",
                "use_brain_retrieval": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["retrieval_mode"] == "brain_distributed"

    def test_search_with_temporal_filter(self, client):
        resp = client.post(
            "/v1/memories/search/",
            json={
                "query": "summer trip",
                "temporal_filter": {
                    "start": "2025-06-01T00:00:00",
                    "end": "2025-09-01T00:00:00",
                },
            },
        )
        assert resp.status_code == 200

    def test_search_with_k_alias(self, client):
        resp = client.post(
            "/v1/memories/search/",
            json={"query": "hiking", "k": 5},
        )
        assert resp.status_code == 200

    def test_search_empty_query_rejected(self, client):
        resp = client.post(
            "/v1/memories/search/",
            json={"query": ""},
        )
        assert resp.status_code == 422

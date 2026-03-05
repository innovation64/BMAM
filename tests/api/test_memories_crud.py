"""Tests for /v1/memories/ CRUD endpoints."""

import pytest


class TestCreateMemory:
    def test_create_with_content(self, client):
        resp = client.post(
            "/v1/memories/",
            json={"content": "I love hiking", "user_id": "test"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["message"] == "Memory created successfully"

    def test_create_with_messages(self, client):
        resp = client.post(
            "/v1/memories/",
            json={
                "messages": [
                    {"role": "user", "content": "I went hiking yesterday"},
                    {"role": "assistant", "content": "That sounds fun!"},
                ],
                "user_id": "test",
            },
        )
        assert resp.status_code == 201

    def test_create_empty_body_fails(self, client):
        resp = client.post("/v1/memories/", json={})
        # resolved_content() raises ValueError → 422 or 500
        assert resp.status_code in (422, 500)


class TestGetMemory:
    def test_get_existing(self, client):
        resp = client.get("/v1/memories/mem-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "mem-001"
        assert data["content"] == "I love hiking"

    def test_get_not_found(self, client, mock_coordinator):
        mock_coordinator.memory_system.db_manager.load_memory.return_value = (
            None
        )
        from src.api.dependencies import set_adapter
        from src.api.middleware_adapter import MiddlewareAdapter

        set_adapter(MiddlewareAdapter(mock_coordinator))
        resp = client.get("/v1/memories/nonexistent")
        assert resp.status_code == 404


class TestListMemories:
    def test_list_default(self, client):
        resp = client.get("/v1/memories/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["memories"]) == 1
        assert data["page"] == 1

    def test_list_pagination(self, client):
        resp = client.get("/v1/memories/?page=1&page_size=10")
        assert resp.status_code == 200


class TestUpdateMemory:
    def test_update_content(self, client):
        resp = client.put(
            "/v1/memories/mem-001",
            json={"content": "I love mountain hiking"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "mem-001"

    def test_update_not_found(self, client, mock_coordinator):
        mock_coordinator.memory_system.update_memory.return_value = False
        from src.api.dependencies import set_adapter
        from src.api.middleware_adapter import MiddlewareAdapter

        set_adapter(MiddlewareAdapter(mock_coordinator))
        resp = client.put(
            "/v1/memories/nonexistent",
            json={"content": "new"},
        )
        assert resp.status_code == 404


class TestDeleteMemory:
    def test_delete_existing(self, client):
        resp = client.delete("/v1/memories/mem-001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "mem-001"

    def test_delete_not_found(self, client, mock_coordinator):
        mock_coordinator.memory_system.delete_memory.return_value = False
        from src.api.dependencies import set_adapter
        from src.api.middleware_adapter import MiddlewareAdapter

        set_adapter(MiddlewareAdapter(mock_coordinator))
        resp = client.delete("/v1/memories/nonexistent")
        assert resp.status_code == 404

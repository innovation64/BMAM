"""Tests for /v1/archives/* endpoints."""


class TestExportArchive:
    def test_export(self, client):
        resp = client.post(
            "/v1/archives/export/",
            json={
                "archive_name": "test_soul_v1",
                "description": "Test export",
                "tags": ["test"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestImportArchive:
    def test_import(self, client):
        resp = client.post(
            "/v1/archives/import/",
            json={
                "archive_path": "/tmp/test_archive.bma",
                "validate": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

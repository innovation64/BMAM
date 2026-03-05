"""Tests for /v1/brain/* endpoints."""


class TestBrainRetrieve:
    def test_basic_retrieve(self, client):
        resp = client.post(
            "/v1/brain/retrieve/",
            json={"query": "What happened last summer?", "k": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["path_type"] in ("fast", "slow")
        assert data["confidence"] > 0
        assert "memories" in data

    def test_retrieve_with_activation_plan(self, client):
        resp = client.post(
            "/v1/brain/retrieve/",
            json={
                "query": "emotional event",
                "activation_plan": {
                    "hippocampus": True,
                    "amygdala": True,
                    "prefrontal": False,
                },
            },
        )
        assert resp.status_code == 200

    def test_retrieve_force_slow_path(self, client):
        resp = client.post(
            "/v1/brain/retrieve/",
            json={
                "query": "complex temporal question",
                "force_slow_path": True,
            },
        )
        assert resp.status_code == 200


class TestProcessInput:
    def test_basic_process(self, client):
        resp = client.post(
            "/v1/brain/process/",
            json={"input": "Tell me about my hobbies", "user_id": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["response"]) > 0
        assert "agents_involved" in data


class TestConsolidate:
    def test_consolidate_default(self, client):
        resp = client.post("/v1/brain/consolidate/")
        assert resp.status_code == 200

    def test_consolidate_with_params(self, client):
        resp = client.post(
            "/v1/brain/consolidate/",
            json={"strategy": "batch", "evaluation_mode": True},
        )
        assert resp.status_code == 200


class TestForget:
    def test_forget_default(self, client):
        resp = client.post("/v1/brain/forget/")
        assert resp.status_code == 200

    def test_forget_with_threshold(self, client):
        resp = client.post(
            "/v1/brain/forget/",
            json={"capacity_threshold": 0.9},
        )
        assert resp.status_code == 200


class TestFeedback:
    def test_apply_feedback(self, client):
        resp = client.post(
            "/v1/brain/feedback/",
            json={
                "query_type": "temporal",
                "reward_signal": 0.8,
                "query": "When did I start hiking?",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert data["weight_delta"] > 0


class TestPreferences:
    def test_get_preferences(self, client):
        resp = client.get(
            "/v1/brain/preferences/",
            params={"query": "hobbies", "user_id": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "hiking" in data["preferences"]

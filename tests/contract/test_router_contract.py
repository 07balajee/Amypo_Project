def test_health_returns_ok(router_client):
    resp = router_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_resource_status_shape(router_client):
    resp = router_client.get("/api/v1/resource-status")
    assert resp.status_code == 200
    body = resp.json()
    for field in ("ram_available_mb", "cpu_load_pct", "bandwidth_kbps", "api_quota_remaining", "source", "sampled_at"):
        assert field in body
    assert body["source"] in ("live", "scenario", "manual")


def test_route_required_fields_present(router_client):
    resp = router_client.post(
        "/api/v1/route", json={"request_id": "r-001", "query": "Explain quicksort"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"] == "r-001"
    assert body["routed_to"] in ("local_model", "cloud_api", "cache", "offline_fallback")
    assert isinstance(body["reasoning"], str) and body["reasoning"]
    assert isinstance(body["latency_ms"], int)
    assert isinstance(body["estimated_cost"], (int, float))
    assert "response" in body
    assert "meta" in body
    assert set(body["meta"].keys()) >= {
        "complexity", "complexity_prob", "candidates", "replanned", "cache_level", "tokens_in", "tokens_out"
    }


def test_route_dry_run_skips_generation(router_client):
    resp = router_client.post(
        "/api/v1/route",
        json={"request_id": "r-002", "query": "Explain quicksort", "dry_run": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == ""
    assert body["meta"]["tokens_out"] == 0


def test_route_strict_contract_strips_extra_fields(router_client, monkeypatch):
    from app.router import api as router_api

    router_api.app.state.settings.strict_contract = True
    try:
        resp = router_client.post(
            "/api/v1/route", json={"request_id": "r-003", "query": "hi"}
        )
        body = resp.json()
        assert "response" not in body
        assert "meta" not in body
        assert "routed_to" in body
    finally:
        router_api.app.state.settings.strict_contract = False


def test_admin_simulate_and_resource_status_reflect_override(router_client):
    resp = router_client.post(
        "/api/v1/admin/simulate", json={"mode": "manual", "bandwidth_kbps": 32}
    )
    assert resp.status_code == 200

    status = router_client.get("/api/v1/resource-status").json()
    assert status["bandwidth_kbps"] == 32
    assert status["source"] == "manual"


def test_admin_decisions_logs_route_calls(router_client):
    router_client.post("/api/v1/route", json={"request_id": "r-004", "query": "hi"})
    resp = router_client.get("/api/v1/admin/decisions?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert any(d["request_id"] == "r-004" for d in body)

def test_health_returns_ok(qa_client):
    resp = qa_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ask_abstains_with_required_shape(qa_client):
    resp = qa_client.post("/api/v1/ask", json={"question": "What is the meaning of life?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "I couldn't find this in AMYPO's records."
    assert body["sources"] == []
    assert body["confidence"] == 0.0
    assert body["meta"]["abstained"] is True
    assert body["meta"]["path"] == "abstain"


def test_ask_accepts_optional_fields(qa_client):
    resp = qa_client.post(
        "/api/v1/ask",
        json={"question": "hi", "user_id": "S2023CS041", "conversation_id": "c-1"},
    )
    assert resp.status_code == 200


def test_admin_reindex_stub(qa_client):
    resp = qa_client.post("/api/v1/admin/reindex")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

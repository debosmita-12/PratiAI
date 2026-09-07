import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") in ["ok", "healthy"]

def test_auth_login():
    res = client.post("/auth/token", data={"username": "debosmita12@gmail.com", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test protected endpoints
    stations_res = client.get("/stations", headers=headers)
    assert stations_res.status_code == 200
    assert isinstance(stations_res.json(), list)

    sections_res = client.get("/sections", headers=headers)
    assert sections_res.status_code == 200
    assert isinstance(sections_res.json(), list)

    plans_res = client.get("/plans/optimized", headers=headers)
    assert plans_res.status_code == 200
    assert isinstance(plans_res.json(), list)

    conflicts_res = client.get("/plans/conflicts", headers=headers)
    assert conflicts_res.status_code == 200
    assert isinstance(conflicts_res.json(), list)

    integrations_res = client.get("/data-integrations/status", headers=headers)
    assert integrations_res.status_code == 200
    assert "integrations" in integrations_res.json()

    models_res = client.get("/models/health", headers=headers)
    assert models_res.status_code == 200

def test_plan_generation():
    login_res = client.post("/auth/token", data={"username": "debosmita12@gmail.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    gen_res = client.post("/plans/generate", json={"horizon": "weekly", "objective_profile": "safety_first"}, headers=headers)
    assert gen_res.status_code == 200
    data = gen_res.json()
    assert data["status"] in ["OPTIMAL", "FEASIBLE", "HEURISTIC_FALLBACK"]
    assert "plan" in data
    assert isinstance(data["plan"], list)

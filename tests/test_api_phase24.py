"""Unit tests for Phase 24 FastAPI application and endpoints."""
import pytest
from fastapi.testclient import TestClient

from episwarm.api.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "episwarm-api"


def test_list_regions_endpoint():
    resp = client.get("/api/regions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    region_ids = [r["id"] for r in data]
    assert "example_synthetic" in region_ids


def test_list_scenarios_endpoint():
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    scen_ids = [s["id"] for s in data]
    assert "baseline" in scen_ids
    assert "targeted_containment" in scen_ids


def test_validation_card_endpoint():
    resp = client.get("/api/validation-card")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("UNCALIBRATED", "PARTIALLY_VALIDATED", "VALIDATED")
    assert "targets" in data


def test_assumptions_endpoint():
    resp = client.get("/api/assumptions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    for a in data:
        assert "parameter" in a
        assert "value" in a
        assert "source" in a
        assert "status" in a


def test_history_endpoints():
    resp = client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_diorama_topology_endpoint():
    resp = client.get("/api/diorama?region_id=example_synthetic")
    assert resp.status_code == 200
    data = resp.json()
    assert "boroughs" in data
    assert "layers" in data
    assert len(data["boroughs"]) > 0
    b0 = data["boroughs"][0]
    assert "iso_x" in b0 and "iso_y" in b0


def test_simulation_endpoint_behavior_modes():
    """Verify endpoint runs across behavior modes: none, rule."""
    payload = {
        "region_id": "example_synthetic",
        "disease_id": "respiratory_generic",
        "scenario_id": "targeted_containment",
        "scale_agents": 1000,
        "behavior_mode": "none",
        "n_replicates": 2,
        "horizon_days": 10
    }
    resp_none = client.post("/api/simulate", json=payload)
    assert resp_none.status_code == 200
    data_none = resp_none.json()
    assert "metrics" in data_none
    assert "attack_rate" in data_none["metrics"]
    assert "timeseries" in data_none

    payload["behavior_mode"] = "rule"
    resp_rule = client.post("/api/simulate", json=payload)
    assert resp_rule.status_code == 200
    data_rule = resp_rule.json()
    assert data_rule["behavior_mode"] == "rule"


def test_whatif_endpoint():
    payload = {
        "region_id": "example_synthetic",
        "disease_id": "respiratory_generic",
        "scenario_a": "baseline",
        "scenario_b": "targeted_containment",
        "scale_agents": 1000,
        "n_replicates": 2
    }
    resp = client.post("/api/what-if", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "comparison" in data
    assert "delta_attack_rate" in data["comparison"]
    assert "delta_deaths" in data["comparison"]

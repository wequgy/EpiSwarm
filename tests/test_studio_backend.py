"""Tests for EpiSwarm Studio FastAPI backend and Stitch UI integration."""

import pytest
from fastapi.testclient import TestClient
from episwarm.studio.app import app

client = TestClient(app)


def test_studio_status_endpoint():
    """Verify system status reports available region packs and Stitch theme."""
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "Field Dispatch Blueprint" in data["theme"]
    assert "example_synthetic" in data["available_regions"]
    assert "respiratory_generic.yaml" in data["available_diseases"]


def test_studio_simulate_and_cache():
    """Verify simulation run endpoint returns real telemetry and caches it."""
    payload = {
        "region_dir": "regions/example_synthetic",
        "disease_path": "diseases/respiratory_generic.yaml",
        "scenario_path": "scenarios/baseline.yaml",
        "population_scale": 1000,
        "r0": 2.5,
        "horizon_days": 15,
        "compliance": 0.70,
        "random_seed": 42
    }
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["scenario_name"] in ["baseline", "Baseline Unmitigated"]
    assert data["total_population"] == 1000
    assert data["horizon_days"] == 15
    assert len(data["daily_metrics"]) == 15
    assert "active_cases" in data["daily_metrics"][0]
    assert "hospitals" in data
    assert len(data["hospitals"]) == 3
    assert len(data["sampled_agents"]) > 0

    # Check cached results endpoint
    cache_res = client.get("/api/current_results")
    assert cache_res.status_code == 200
    cache_data = cache_res.json()
    assert cache_data["run_id"] == data["run_id"]


def test_studio_showcase_agents():
    """Verify showcase agents endpoint includes required synthetic disclaimers."""
    res = client.get("/api/agents?limit=3")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) == 3
    for a in agents:
        assert "name" in a
        assert "role" in a
        assert "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY]" in a["biography"]


def test_studio_static_files():
    """Verify that static UI files (HTML, CSS, JS) are properly mounted and served."""
    res_html = client.get("/")
    assert res_html.status_code == 200
    res_upper = res_html.text.upper()
    assert "EPISWARM" in res_upper
    assert "BENGALURU" in res_upper or "FIELD DISPATCH BLUEPRINT" in res_upper

    res_css = client.get("/studio.css")
    assert res_css.status_code == 200
    assert "Inter" in res_css.text or "Bricolage Grotesque" in res_css.text

    res_js = client.get("/studio.js")
    assert res_js.status_code == 200
    assert "EpiSwarm Studio" in res_js.text


def test_studio_advisor_endpoint():
    """Verify policy advisor endpoint returns valid recommendation structure."""
    res = client.post("/api/advisor")
    assert res.status_code == 200
    data = res.json()
    assert "priority_areas" in data
    assert "recommended_measures" in data
    assert "predicted_deaths_reduction" in data

"""Contract tests for EpiSwarm API v1 routers and services (Stage B1)."""

import time
import pytest
from fastapi.testclient import TestClient

from episwarm.api.main import app

client = TestClient(app)


# ==============================================================================
# 1. System & Health Endpoints
# ==============================================================================

def test_v1_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "episwarm-api"
    assert "timestamp" in data


def test_v1_backends():
    resp = client.get("/api/v1/backends")
    assert resp.status_code == 200
    data = resp.json()
    assert "backends" in data
    names = [b["name"] for b in data["backends"]]
    assert "engine_abm" in names
    assert "gemini" in names
    assert "sqlite_jobs" in names

    # Verify no confidential API keys are leaked
    for b in data["backends"]:
        assert "api_key" not in b
        assert "key" not in b
        details = b.get("details", {})
        assert "api_key" not in details
        assert "secret" not in details


# ==============================================================================
# 2. Trust & Validation Endpoints
# ==============================================================================

def test_v1_validation_card():
    resp = client.get("/api/v1/validation/card")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("UNCALIBRATED", "PARTIALLY_VALIDATED", "VALIDATED")
    assert "targets" in data


def test_v1_validation_report():
    resp = client.get("/api/v1/validation/report")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "report_markdown" in data
    assert len(data["report_markdown"]) > 0
    assert "assumptions_count" in data


def test_v1_validation_assumptions():
    resp = client.get("/api/v1/validation/assumptions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    for a in data:
        assert "parameter" in a
        assert "value" in a
        assert "status" in a
        assert a["status"] == "ASSUMED"


def test_v1_validation_evidence():
    resp = client.get("/api/v1/validation/evidence")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        rec = data[0]
        assert "sha256" in rec
        assert "file_path" in rec
        assert rec["record_status"] == "verified"


# ==============================================================================
# 3. Pack Inspection & Validation Endpoints
# ==============================================================================

def test_v1_packs_regions():
    resp = client.get("/api/v1/packs/regions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = [r["id"] for r in data]
    assert "example_synthetic" in ids

    # Single region detail
    resp_one = client.get("/api/v1/packs/regions/example_synthetic")
    assert resp_one.status_code == 200
    assert resp_one.json()["id"] == "example_synthetic"

    # Region validation endpoint
    resp_val = client.post("/api/v1/packs/regions/example_synthetic/validate")
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert "is_valid" in val_data
    assert val_data["pack_id"] == "example_synthetic"


def test_v1_packs_diseases():
    resp = client.get("/api/v1/packs/diseases")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [d["id"] for d in data]
    assert "respiratory_generic" in ids

    # Disease detail
    resp_one = client.get("/api/v1/packs/diseases/respiratory_generic")
    assert resp_one.status_code == 200
    assert resp_one.json()["name"] == "respiratory_generic"

    # Disease validation
    resp_val = client.post("/api/v1/packs/diseases/respiratory_generic/validate")
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert val_data["is_valid"] is True


def test_v1_packs_scenarios():
    resp = client.get("/api/v1/packs/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [s["id"] for s in data]
    assert "baseline" in ids
    assert "targeted_containment" in ids

    # Scenario detail
    resp_one = client.get("/api/v1/packs/scenarios/targeted_containment")
    assert resp_one.status_code == 200

    # Scenario validation
    resp_val = client.post("/api/v1/packs/scenarios/targeted_containment/validate")
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert val_data["is_valid"] is True


def test_v1_packs_behaviors():
    resp = client.get("/api/v1/packs/behaviors")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    # Behavior validation
    resp_val = client.post("/api/v1/packs/behaviors/default/validate")
    assert resp_val.status_code == 200
    assert resp_val.json()["is_valid"] is True


# ==============================================================================
# 4. Simulation Runs & Mock Execution
# ==============================================================================

def test_v1_runs_mock_lifecycle():
    """Test full asynchronous lifecycle and outputs with fast synthetic mock fixture."""
    payload = {
        "region_id": "example_synthetic",
        "disease_id": "respiratory_generic",
        "scenario_id": "targeted_containment",
        "scale_agents": 1000,
        "behavior_mode": "rule",
        "n_replicates": 3,
        "horizon_days": 30,
        "use_mock": True,
    }

    # 1. Launch Job
    resp_launch = client.post("/api/v1/runs", json=payload)
    assert resp_launch.status_code == 201
    assert resp_launch.headers.get("x-episwarm-mock") == "true"
    job = resp_launch.json()
    job_id = job["job_id"]
    assert job["is_mock"] is True

    # Allow worker thread a brief tick to process mock run
    for _ in range(20):
        resp_check = client.get(f"/api/v1/runs/{job_id}")
        if resp_check.json()["status"] == "COMPLETED":
            break
        time.sleep(0.1)

    # 2. Get Job Details
    resp_job = client.get(f"/api/v1/runs/{job_id}")
    assert resp_job.status_code == 200
    data_job = resp_job.json()
    assert data_job["status"] == "COMPLETED"
    assert data_job["progress"] == 1.0

    # 3. List Runs
    resp_list = client.get("/api/v1/runs?limit=10")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total"] >= 1
    found_ids = [j["job_id"] for j in list_data["jobs"]]
    assert job_id in found_ids

    # 4. Get Summary
    resp_summary = client.get(f"/api/v1/runs/{job_id}/summary")
    assert resp_summary.status_code == 200
    assert resp_summary.headers.get("x-episwarm-mock") == "true"
    summary = resp_summary.json()
    assert summary["job_id"] == job_id
    assert "metrics" in summary
    assert "attack_rate" in summary["metrics"]
    assert "peak_day" in summary["metrics"]
    assert "total_deaths" in summary["metrics"]
    assert summary["is_mock"] is True
    assert "MOCK DATA" in summary["banner"]

    # 5. Get TimeSeries
    resp_ts = client.get(f"/api/v1/runs/{job_id}/timeseries")
    assert resp_ts.status_code == 200
    ts = resp_ts.json()
    assert len(ts["days"]) == 31
    assert "S" in ts["daily_states"]
    assert len(ts["daily_hospital_demand"]) == 31
    assert len(ts["daily_icu_demand"]) == 31

    # 6. Get Spatial
    resp_spatial = client.get(f"/api/v1/runs/{job_id}/spatial")
    assert resp_spatial.status_code == 200
    spatial = resp_spatial.json()
    assert spatial["n_areas"] > 0
    assert len(spatial["layers"]) >= 4
    a0 = spatial["areas"][0]
    assert "iso_x" in a0 and "iso_y" in a0
    assert "attack_rate" in a0

    # 7. Get Capacity
    resp_cap = client.get(f"/api/v1/runs/{job_id}/capacity")
    assert resp_cap.status_code == 200
    cap = resp_cap.json()
    assert cap["hospital_capacity_beds"] > 0
    assert cap["icu_capacity_beds"] > 0
    assert len(cap["daily_hospital_demand"]) > 0

    # 8. Test SSE Events
    resp_events = client.get(f"/api/v1/runs/{job_id}/events")
    assert resp_events.status_code == 200
    assert "text/event-stream" in resp_events.headers["content-type"]
    assert "event: complete" in resp_events.text or "event: status" in resp_events.text


def test_v1_runs_real_fast_simulation():
    """Verify engine execution facade runs a real simulation and generates outputs."""
    payload = {
        "region_id": "example_synthetic",
        "disease_id": "respiratory_generic",
        "scenario_id": "baseline",
        "scale_agents": 500,
        "behavior_mode": "none",
        "n_replicates": 1,
        "horizon_days": 5,
        "use_mock": False,
    }
    resp = client.post("/api/v1/runs", json=payload)
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]

    # Poll for completion (should take ~0.5s for 500 agents and 5 days)
    for _ in range(50):
        status_resp = client.get(f"/api/v1/runs/{job_id}")
        st = status_resp.json()["status"]
        if st in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.1)

    assert status_resp.json()["status"] == "COMPLETED"

    # Verify real summary
    sum_resp = client.get(f"/api/v1/runs/{job_id}/summary")
    assert sum_resp.status_code == 200
    assert sum_resp.json()["is_mock"] is False


def test_v1_runs_cancel():
    """Verify job cancellation endpoint."""
    payload = {
        "region_id": "example_synthetic",
        "disease_id": "respiratory_generic",
        "scenario_id": "targeted_containment",
        "scale_agents": 2000,
        "n_replicates": 5,
        "horizon_days": 60,
    }
    resp = client.post("/api/v1/runs", json=payload)
    job_id = resp.json()["job_id"]

    cancel_resp = client.post(f"/api/v1/runs/{job_id}/cancel")
    assert cancel_resp.status_code == 200
    data = cancel_resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "CANCELLED"


# ==============================================================================
# 5. Counterfactual Comparison & What-If
# ==============================================================================

def test_v1_compare_and_whatif():
    payload = {
        "region_id": "example_synthetic",
        "disease_id": "respiratory_generic",
        "scenario_a": "baseline",
        "scenario_b": "targeted_containment",
        "scale_agents": 500,
        "n_replicates": 2,
        "random_seed": 42,
    }

    # /compare
    resp_comp = client.post("/api/v1/compare", json=payload)
    assert resp_comp.status_code == 200
    data_comp = resp_comp.json()
    assert data_comp["scenario_a"] == "baseline"
    assert data_comp["scenario_b"] == "targeted_containment"
    assert "delta_means" in data_comp
    assert "comparison" in data_comp

    # /what-if alias
    resp_wi = client.post("/api/v1/what-if", json=payload)
    assert resp_wi.status_code == 200
    data_wi = resp_wi.json()
    assert "delta_means" in data_wi


# ==============================================================================
# 6. RFC 7807 Problem Details Error Handling
# ==============================================================================

def test_v1_rfc7807_not_found():
    """Verify 404 returns application/problem+json."""
    resp = client.get("/api/v1/runs/job_nonexistent_999999")
    assert resp.status_code == 404
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 404
    assert data["title"] == "Not Found"
    assert "job_nonexistent_999999" in data["detail"]
    assert data["instance"] == "/api/v1/runs/job_nonexistent_999999"


def test_v1_rfc7807_validation_error():
    """Verify 422 returns application/problem+json with invalid_params."""
    payload = {
        "region_id": "example_synthetic",
        "scale_agents": 10,  # Invalid: ge=100
    }
    resp = client.post("/api/v1/runs", json=payload)
    assert resp.status_code == 422
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 422
    assert data["title"] == "Unprocessable Entity"
    assert "invalid_params" in data
    assert len(data["invalid_params"]) > 0


def test_v1_rfc7807_pack_not_found():
    """Verify 404 on nonexistent pack returns application/problem+json."""
    resp = client.get("/api/v1/packs/regions/nonexistent_region_xyz")
    assert resp.status_code == 404
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 404
    assert data["title"] == "Not Found"


# ==============================================================================
# 7. Production SPA Static Serving & Fallback Routing
# ==============================================================================

def test_v1_spa_serving():
    """Verify FastAPI root and client-side fallback routes serve Vite SPA."""
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "text/html" in resp_root.headers.get("content-type", "")
    assert '<div id="root">' in resp_root.text

    resp_client_route = client.get("/runs")
    assert resp_client_route.status_code == 200
    assert '<div id="root">' in resp_client_route.text

    resp_api_404 = client.get("/api/v1/nonexistent_subroute")
    assert resp_api_404.status_code == 404
    assert resp_api_404.headers["content-type"] == "application/problem+json"


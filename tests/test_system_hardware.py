"""Tests for hardware probe and resource estimation (Stage R3.2)."""

import pytest
from fastapi.testclient import TestClient

from episwarm.system.hardware import probe_hardware, probe_gpu, estimate_resources
from episwarm.api.main import app


def test_hardware_probe_structure():
    hw = probe_hardware()
    assert "cpu" in hw
    assert hw["cpu"]["logical_cores"] >= 1
    assert hw["cpu"]["physical_cores"] >= 1
    assert "memory" in hw
    assert hw["memory"]["total_bytes"] > 0
    assert hw["memory"]["budget_limit_bytes"] == 11 * 1024 * 1024 * 1024
    assert "gpu" in hw
    assert "runtime" in hw
    assert "recommendations" in hw
    assert hw["recommendations"]["recommended_workers"] >= 1
    assert hw["recommendations"]["default_scale_agents"] == 50000


def test_estimate_resources():
    est = estimate_resources(agents=50000, days=60, replicates=5)
    assert est["estimated_memory_mb"] > 0
    assert est["fits_memory_budget"] is True
    assert est["estimated_wall_time_seconds"] > 0


def test_api_v1_system_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/system")
    assert resp.status_code == 200
    data = resp.json()
    assert "cpu" in data
    assert "recommendations" in data

    resp_est = client.get("/api/v1/system/estimate?agents=10000&days=30&replicates=2")
    assert resp_est.status_code == 200
    est_data = resp_est.json()
    assert est_data["inputs"]["agents"] == 10000
    assert est_data["fits_memory_budget"] is True

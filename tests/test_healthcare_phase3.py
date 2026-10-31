"""Unit and invariant tests for Phase 3: healthcare capacity, spatial routing, and overflow mortality."""

import numpy as np
import pandas as pd
import pytest

from episwarm.packs.disease import OverflowMortalityConfig
from episwarm.engine.healthcare import RegionalHealthcareSystem


def test_healthcare_overflow_known_capacity():
    # 2 areas: A01 has 30 beds, A02 has 20 beds (Total 50 beds)
    cap_df = pd.DataFrame([
        {"area_id": "A01", "category": "general", "nominal": 30},
        {"area_id": "A02", "category": "general", "nominal": 20}
    ])
    areas_df = pd.DataFrame([
        {"area_id": "A01", "lat": 10.0, "lon": 10.0},
        {"area_id": "A02", "lat": 10.1, "lon": 10.1}
    ])
    area_map = {"A01": 0, "A02": 1}
    overflow_cfg = OverflowMortalityConfig(
        bed_unavailable_mortality_multiplier=2.5,
        compliance_mortality_benefit=0.8,
        non_compliance_mortality_penalty=1.2
    )
    system = RegionalHealthcareSystem(
        cap_df, None, areas_df, area_map, overflow_cfg,
        external_inflow_fraction=0.0  # Zero external inflow for exact counting test
    )

    # 1. Test demand below capacity: 40 patients in A01
    patients_origin = np.zeros(40, dtype=np.int16)
    compliances = np.full(40, 0.5, dtype=np.float32)

    is_served, mort_mults, unmet = system.route_patients(
        needed_category=1,
        patient_areas=patients_origin,
        patient_compliances=compliances
    )
    # A01 takes 30, overflows 10 to A02 -> all 40 served!
    assert unmet == 0
    assert np.all(is_served)
    assert np.all(mort_mults == 1.0)

    # 2. Test demand above capacity: 70 patients in A01
    patients_origin_70 = np.zeros(70, dtype=np.int16)
    compliances_70 = np.full(70, 1.0, dtype=np.float32)  # fully compliant

    is_served_70, mort_mults_70, unmet_70 = system.route_patients(
        needed_category=1,
        patient_areas=patients_origin_70,
        patient_compliances=compliances_70
    )
    # Total capacity is 50. Unmet must be 20.
    assert unmet_70 == 20
    assert np.sum(is_served_70) == 50
    assert np.sum(~is_served_70) == 20

    # Unserved fully compliant patients get multiplier: 2.5 * 0.8 = 2.0
    unserved_mults = mort_mults_70[~is_served_70]
    np.testing.assert_allclose(unserved_mults, 2.0, rtol=1e-5)


def test_compliance_mortality_benefit_vs_penalty():
    cap_df = pd.DataFrame([
        {"area_id": "A01", "category": "icu", "nominal": 0}  # Zero capacity -> all unserved
    ])
    areas_df = pd.DataFrame([{"area_id": "A01", "lat": 0.0, "lon": 0.0}])
    area_map = {"A01": 0}
    overflow_cfg = OverflowMortalityConfig(
        icu_unavailable_mortality_multiplier=3.0,
        compliance_mortality_benefit=0.70,
        non_compliance_mortality_penalty=1.30
    )
    system = RegionalHealthcareSystem(
        cap_df, None, areas_df, area_map, overflow_cfg, external_inflow_fraction=0.0
    )

    # Patient 0: Compliant (1.0), Patient 1: Non-compliant (0.0)
    patients = np.zeros(2, dtype=np.int16)
    comps = np.array([1.0, 0.0], dtype=np.float32)

    _, mults, unmet = system.route_patients(3, patients, comps)
    assert unmet == 2
    # Compliant: 3.0 * 0.70 = 2.10
    # Non-compliant: 3.0 * 1.30 = 3.90
    assert mults[0] < mults[1]
    assert abs(mults[0] - 2.10) < 1e-5
    assert abs(mults[1] - 3.90) < 1e-5

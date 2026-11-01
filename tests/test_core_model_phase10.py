"""Unit and acceptance tests for Phase 10: Core Model Changes.

Acceptance criteria (Roadmap Section 4 & Spec 5, 6, 9):
1. Grep test: No resource-specific (including oxygen) or disease-specific hardcoded names in src/.
2. Two disease packs test: Engine runs two packs with distinct vulnerability factors and environment modifiers, producing different, explainable outcomes.
3. Unserved patient outcomes: Multi-factor formula where theta_0 = 0 makes unserved equal served, and large theta_care differentiates low vs high self-care agents.
4. Agent life histories: Generated structured facts, reproducible by seed, and showcase profile generation.
5. Generic resources: Multi-resource allocation and upper_cap_of_extra enforcement.
"""

from pathlib import Path
import re
import pytest
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population, PopulationSoA
from episwarm.packs.disease import DiseasePack, UnservedOutcomeConfig
from episwarm.packs.scenario import ScenarioPack, ResourceAddAction
from episwarm.engine.resources import RegionalResourceSystem, calculate_adverse_probability
from episwarm.engine.sim import run_simulation


def test_grep_no_forbidden_resource_or_disease_names_in_src():
    """Acceptance criterion 1: Grep test verifying src/ has zero hardcoded resource names (like oxygen)."""
    src_dir = Path("src")
    assert src_dir.exists(), "src/ directory must exist"

    forbidden_patterns = [
        re.compile(r"\boxygen\b", re.IGNORECASE),
        re.compile(r"\bventilator\b", re.IGNORECASE),
        re.compile(r"\bcovid\b", re.IGNORECASE),
        re.compile(r"\bcoronavirus\b", re.IGNORECASE),
    ]

    violations = []
    for py_file in src_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pat in forbidden_patterns:
            matches = list(pat.finditer(text))
            for m in matches:
                violations.append(f"{py_file}:{m.start()} found '{m.group()}'")

    assert len(violations) == 0, f"Found forbidden hardcoded names in src/:\n" + "\n".join(violations)


def test_two_disease_packs_different_vulnerability_and_environment():
    """Acceptance criterion 2: Same engine runs two disease packs with distinct vulnerability factors and environment modifiers."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=101)
    env_df = pd.read_csv("regions/example_synthetic/environment.csv")
    res_df = pd.read_csv("regions/example_synthetic/resources.csv")

    # 1. Run respiratory_generic (has hypertension & respiratory_chronic factors, persons_per_room modifier = 0.25)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d1 = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s1 = ScenarioPack(**yaml.safe_load(f))
        s1.horizon_days = 25

    res1 = run_simulation(pop, d1, s1, resources_df=res_df, environment_df=env_df)

    # 2. Run influenza_generic (has pediatric_asthma factor, persons_per_room modifier = 0.10, shorter duration)
    with open("diseases/influenza_generic.yaml", "r", encoding="utf-8") as f:
        d2 = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s2 = ScenarioPack(**yaml.safe_load(f))
        s2.horizon_days = 25

    res2 = run_simulation(pop, d2, s2, resources_df=res_df, environment_df=env_df)

    # Both must run to completion with valid epidemic progression
    assert res1.total_infections > 0
    assert res2.total_infections > 0
    assert res1.disease_name == "respiratory_generic"
    assert res2.disease_name == "influenza_generic"

    # Distinct epidemiological behavior
    assert res1.target_r0 != res2.target_r0
    assert len(d1.vulnerability_factors) == 2
    assert len(d2.vulnerability_factors) == 1
    assert d1.vulnerability_factors[0].id != d2.vulnerability_factors[0].id

    # Curves must be quantitatively different
    assert not np.array_equal(res1.daily_state_counts, res2.daily_state_counts)


def test_unserved_patient_outcomes_individual_factors():
    """Acceptance criterion 3: Multi-factor individual patient outcomes for unserved patients (Spec 6.3)."""
    p_served = 0.05

    # Case A: When theta_0 = 0 and other thetas = 0, unserved adverse prob == served adverse prob
    cfg_zero = UnservedOutcomeConfig(
        theta_0=0.0, theta_sev=0.0, theta_care=0.0, theta_sup=0.0, theta_alt=0.0, theta_delay=0.0
    )
    p_unserved_zero = calculate_adverse_probability(
        p_served=p_served,
        service_level=0.0,  # Completely unserved
        severity_level=1.0,
        self_care=0.1,
        support=0.1,
        alt_care=0.1,
        unserved_days=10,
        config=cfg_zero
    )
    assert pytest.approx(p_unserved_zero, rel=1e-4) == p_served

    # Case B: Under identical overflow (service_level = 0.0), large theta_care causes
    # low self-care agents to suffer worse outcomes than high self-care agents
    cfg_care = UnservedOutcomeConfig(
        theta_0=0.5, theta_sev=0.0, theta_care=2.0, theta_sup=0.0, theta_alt=0.0, theta_delay=0.0
    )
    p_low_care = calculate_adverse_probability(
        p_served=p_served,
        service_level=0.0,
        severity_level=1.0,
        self_care=0.10,  # Low self-care
        support=0.50,
        alt_care=0.50,
        unserved_days=0,
        config=cfg_care
    )
    p_high_care = calculate_adverse_probability(
        p_served=p_served,
        service_level=0.0,
        severity_level=1.0,
        self_care=0.90,  # High self-care
        support=0.50,
        alt_care=0.50,
        unserved_days=0,
        config=cfg_care
    )
    assert p_low_care > p_high_care
    assert p_low_care >= 2.0 * p_high_care, "Low self-care should face significantly worse outcomes under saturated care"

    # Case C: Delay accumulation increases adverse probability monotonically
    cfg_delay = UnservedOutcomeConfig(
        theta_0=0.5, theta_sev=0.0, theta_care=0.0, theta_sup=0.0, theta_alt=0.0, theta_delay=0.3
    )
    p_delay_0 = calculate_adverse_probability(p_served, 0.0, 1.0, 0.5, 0.5, 0.5, unserved_days=0, config=cfg_delay)
    p_delay_3 = calculate_adverse_probability(p_served, 0.0, 1.0, 0.5, 0.5, 0.5, unserved_days=3, config=cfg_delay)
    p_delay_7 = calculate_adverse_probability(p_served, 0.0, 1.0, 0.5, 0.5, 0.5, unserved_days=7, config=cfg_delay)
    assert p_delay_0 < p_delay_3 < p_delay_7


def test_life_history_fields_generation_and_reproducibility():
    """Acceptance criterion 4: Life history fields generation, bounds, and seed reproducibility (Spec 9)."""
    # 1. Reproducibility across seeds
    pop1 = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    pop2 = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)

    np.testing.assert_array_equal(pop1.income_band, pop2.income_band)
    np.testing.assert_array_equal(pop1.household_role, pop2.household_role)
    np.testing.assert_array_equal(pop1.routine_template, pop2.routine_template)
    np.testing.assert_array_equal(pop1.pref_market_id, pop2.pref_market_id)
    np.testing.assert_array_equal(pop1.pref_leisure_id, pop2.pref_leisure_id)
    np.testing.assert_array_equal(pop1.caregiver, pop2.caregiver)
    np.testing.assert_array_equal(pop1.past_bereavement, pop2.past_bereavement)
    np.testing.assert_allclose(pop1.financial_buffer, pop2.financial_buffer)
    np.testing.assert_allclose(pop1.self_care, pop2.self_care)
    np.testing.assert_allclose(pop1.support, pop2.support)

    # 2. Value bounds
    assert np.all(np.isin(pop1.income_band, [0, 1, 2]))
    assert np.all(np.isin(pop1.household_role, [0, 1, 2, 3]))
    assert np.all(np.isin(pop1.routine_template, [0, 1, 2, 3, 4, 5]))
    assert np.all((pop1.financial_buffer >= 0.0) & (pop1.financial_buffer <= 1.0))
    assert np.all((pop1.self_care >= 0.0) & (pop1.self_care <= 1.0))
    assert np.all((pop1.support >= 0.0) & (pop1.support <= 1.0))
    assert np.all(pop1.pref_market_id >= 0)
    assert np.all(pop1.pref_leisure_id >= 0)

    # 3. Showcase profile generation (Spec 9)
    profile = pop1.get_showcase_profile(0)
    assert "narrative" in profile
    assert "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY]" in profile["narrative"]
    assert profile["agent_id"] == 0
    assert profile["role"] in ["Child/Dependent", "Primary Earner", "Caregiver Adult", "Elder Resident"]


def test_generic_resources_allocation_and_caps():
    """Acceptance criterion 5: Generic resources allocation, service levels, and upper cap validation (Spec 6.1 & 6.4)."""
    res_df = pd.DataFrame([
        {
            "resource_id": "clinical_bed",
            "nominal": 10.0,
            "effective_low": 8.0,
            "effective_high": 12.0,
            "upper_cap_of_extra": 5.0,
            "area_id": "A01",
            "restock_rate": 0.0
        },
        {
            "resource_id": "support_gear",
            "nominal": 5.0,
            "effective_low": 4.0,
            "effective_high": 6.0,
            "upper_cap_of_extra": 3.0,
            "area_id": "A01",
            "restock_rate": 0.0
        }
    ])
    areas_df = pd.DataFrame([{"area_id": "A01", "lat": 0.0, "lon": 0.0}])
    area_map = {"A01": 0}

    sys = RegionalResourceSystem(resources_df=res_df, areas_df=areas_df, area_id_to_int=area_map)

    # Patient needing both clinical_bed and support_gear
    patient_areas = np.zeros(6, dtype=np.int16)
    needs = [{"clinical_bed": 1.0, "support_gear": 1.0} for _ in range(6)]

    service_levels, adverse_probs, unmet = sys.route_and_allocate(
        patient_areas=patient_areas,
        resource_needs=needs,
        self_care=np.full(6, 0.7, dtype=np.float32),
        support=np.full(6, 0.7, dtype=np.float32),
        alt_care=np.full(6, 0.7, dtype=np.float32),
        unserved_days=np.zeros(6, dtype=np.int16),
        severity_levels=np.full(6, 1.0, dtype=np.float32),
        p_served_adverse=np.full(6, 0.05, dtype=np.float32)
    )

    # 5 patients get allocated (since support_gear capacity is 5.0), 6th patient gets service_level = 0.0
    assert np.sum(service_levels == 1.0) == 5
    assert service_levels[5] == 0.0
    assert unmet["support_gear"] == 1

    # Test Spec 6.4: Upper cap validation
    # Valid addition (within upper_cap_of_extra 5.0)
    valid_add = ResourceAddAction(resource_id="clinical_bed", area_id="A01", amount=4.0)
    sys.apply_resource_addition(valid_add)
    assert sys.pools[0]["clinical_bed"].nominal == 14.0

    # Invalid addition exceeding upper_cap_of_extra
    excess_add = ResourceAddAction(resource_id="clinical_bed", area_id="A01", amount=10.0)
    with pytest.raises(ValueError) as exc:
        sys.apply_resource_addition(excess_add)
    assert "exceeds upper_cap_of_extra" in str(exc.value)


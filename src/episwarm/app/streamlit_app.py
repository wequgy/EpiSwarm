"""EpiSwarm Studio: Interactive Outbreak Simulation & Policy Advisory App (Streamlit + Plotly)."""

import os
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from episwarm.packs.region import RegionPack, RegionMeta, L0QuickInputs
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction, SeedingConfig
from episwarm.packs.behavior import BehaviorPack
from episwarm.importers.quick_region import QuickRegionBuilder
from episwarm.importers.mapper import ColumnMapper
from episwarm.population.build import build_synthetic_population
from episwarm.engine.sim import run_simulation
from episwarm.engine.healthcare import RegionalHealthcareSystem
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.advisor.agent import AdvisorAgent
from episwarm.optimize.search import run_optuna_search
from episwarm.analysis.equity import evaluate_equity
from episwarm.analysis.spread_matrix import compute_spread_matrix
from episwarm.analysis.metrics import evaluate_single_run_objectives
from episwarm.analysis.calibration import calibrate_to_observed_data

# Page config
st.set_page_config(
    page_title="EpiSwarm Studio",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Persistent Banners & Provenance Panel
st.title("🧬 EpiSwarm Studio")
st.caption("Configurable Agent-Based Outbreak Simulation & Multi-Objective Response Planning")

# System Provenance & Honesty Banners
col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    st.warning("⚠️ UNCALIBRATED: Run comparisons are counterfactual under stated assumptions, not real-world forecasts.")
with col_b2:
    st.info("ℹ️ SYNTHETIC DATA: Benchmark fixture active (`example_synthetic`). Not describing a real location.")
with col_b3:
    st.error("🛡️ BEHAVIOR LAYER UNVALIDATED: LLM-driven compliance is hypothetical.")

# Sidebar navigation
st.sidebar.header("Workflow Steps")
step = st.sidebar.radio(
    "Navigation",
    [
        "1. Region & Population",
        "2. Disease State Graph",
        "3. Healthcare & Capacity",
        "4. Interventions & Scenario",
        "5. Simulation Engine",
        "6. Analysis & Equity",
        "7. Policy Advisor & Optimizer",
        "8. Export Audit Report"
    ]
)

# Shared Session State Initialization
if "region_dir" not in st.session_state:
    st.session_state.region_dir = Path("regions/example_synthetic")
if "pop_scale" not in st.session_state:
    st.session_state.pop_scale = 5000
if "sim_results" not in st.session_state:
    st.session_state.sim_results = None
if "pop_soa" not in st.session_state:
    st.session_state.pop_soa = None

# --- STEP 1: REGION & POPULATION ---
if step == "1. Region & Population":
    st.header("Step 1: Region & Synthetic Population Builder")
    tab_preset, tab_l0, tab_upload = st.tabs(["Pre-configured Packs", "Quick Region (L0) Builder", "Upload & Column Mapper"])

    with tab_preset:
        pack_choices = [p.name for p in Path("regions").iterdir() if p.is_dir()]
        chosen = st.selectbox("Select Region Pack", pack_choices, index=0 if pack_choices else None)
        if chosen:
            st.session_state.region_dir = Path("regions") / chosen
            yaml_path = st.session_state.region_dir / "region.yaml"
            if yaml_path.exists():
                with open(yaml_path, "r", encoding="utf-8") as f:
                    meta = yaml.safe_load(f)
                st.json(meta)

    with tab_l0:
        st.subheader("Synthesize Region from High-Level (L0) Indicators")
        col_l0_1, col_l0_2 = st.columns(2)
        with col_l0_1:
            l0_name = st.text_input("Region Name", "custom_quick_region")
            l0_pop = st.number_input("Total Population", value=50000, step=5000)
            l0_areas = st.number_input("Number of Administrative Areas", value=4, min_value=1, max_value=20)
            l0_hh = st.number_input("Average Household Size", value=3.8, min_value=1.0, max_value=10.0)
        with col_l0_2:
            l0_emp = st.slider("Employment Rate", 0.1, 0.9, 0.60)
            l0_beds = st.number_input("Hospital Beds per 1,000", value=2.0, min_value=0.1)
            l0_icu = st.number_input("ICU Beds per 1,000", value=0.2, min_value=0.01)

        if st.button("Generate L0 Quick Region"):
            meta = RegionMeta(name=l0_name, country_iso="GEN", data_year=2024, area_levels=["ward"])
            inputs = L0QuickInputs(
                total_population=int(l0_pop),
                num_areas=int(l0_areas),
                avg_household_size=float(l0_hh),
                employment_rate=float(l0_emp),
                beds_per_1000=float(l0_beds),
                icu_beds_per_1000=float(l0_icu)
            )
            out_dir = Path(f"regions/{l0_name}")
            builder = QuickRegionBuilder(meta, inputs)
            builder.generate_all(out_dir)
            st.session_state.region_dir = out_dir
            st.success(f"Generated L0 Region Pack at {out_dir}")

    with tab_upload:
        st.subheader("Upload Area Data Table")
        st.warning("Privacy Notice: Processed locally. Do not upload personally identifiable health records.")
        uploaded_file = st.file_uploader("Upload areas CSV", type=["csv", "xlsx"])
        if uploaded_file:
            df_up = pd.read_csv(uploaded_file)
            st.write("Uploaded Table Preview:", df_up.head())
            mapping = ColumnMapper.suggest_mapping("areas.csv", list(df_up.columns))
            st.write("Suggested Column Mapping:", mapping)

    st.divider()
    st.subheader("Generate Synthetic Resident Population (SoA)")
    st.session_state.pop_scale = st.select_slider("Simulation Agent Scale", options=[5000, 25000, 50000, 100000], value=5000)
    if st.button("Build Synthetic Population"):
        with st.spinner("Synthesizing population via Structure-of-Arrays (SoA) and IPF..."):
            pop = build_synthetic_population(
                st.session_state.region_dir,
                scale_agents=st.session_state.pop_scale,
                random_seed=42
            )
            st.session_state.pop_soa = pop
            st.text(pop.summary())
            st.success(f"Instantiated {pop.n_agents:,} synthetic agents!")

# --- STEP 2: DISEASE STATE GRAPH ---
elif step == "2. Disease State Graph":
    st.header("Step 2: Disease State Machine & Transmission Presets")
    disease_files = [f.name for f in Path("diseases").glob("*.yaml")]
    chosen_disease = st.selectbox("Select Disease Preset", disease_files, index=0 if disease_files else None)

    if chosen_disease:
        d_path = Path("diseases") / chosen_disease
        with open(d_path, "r", encoding="utf-8") as f:
            d_dict = yaml.safe_load(f)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.subheader("Transmission & Reproduction Number")
            r0_val = st.number_input("Basic Reproduction Number (R0)", value=float(d_dict.get("transmission", {}).get("r0", 2.5)), step=0.1)
            overdisp_k = st.number_input("Overdispersion k (Super-spreading)", value=float(d_dict.get("transmission", {}).get("overdispersion_k", 0.16)), step=0.05)
            st.caption("Lower k indicates higher variance / super-spreading events (Lloyd-Smith et al. 2005).")
        with col_d2:
            st.subheader("Healthcare Overflow Multipliers")
            bed_mult = st.number_input("General Bed Unavailable Multiplier", value=float(d_dict.get("overflow", {}).get("bed_unavailable_mortality_multiplier", 2.0)), step=0.5)
            icu_mult = st.number_input("ICU Bed Unavailable Multiplier", value=float(d_dict.get("overflow", {}).get("icu_unavailable_mortality_multiplier", 3.5)), step=0.5)

        st.subheader("State Compartments")
        st.dataframe(pd.DataFrame(d_dict.get("states", [])))

        st.subheader("State Transitions")
        st.dataframe(pd.DataFrame(d_dict.get("transitions", [])))

# --- STEP 3: HEALTHCARE & CAPACITY ---
elif step == "3. Healthcare & Capacity":
    st.header("Step 3: Hospital Beds, ICU, and Oxygen Buffer")
    cap_file = st.session_state.region_dir / "capacity.csv"
    if cap_file.exists():
        cap_df = pd.read_csv(cap_file)
        st.dataframe(cap_df)

        fig = px.bar(cap_df, x="hospital_id", y="nominal", color="category", barmode="group", title="Nominal Capacity by Facility")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No capacity.csv present. Defaulting to 1.5 general beds and 0.2 ICU beds per 1k population.")

# --- STEP 4: INTERVENTIONS & SCENARIO ---
elif step == "4. Interventions & Scenario":
    st.header("Step 4: Non-Pharmaceutical Interventions & Objectives")
    scen_files = [f.name for f in Path("scenarios").glob("*.yaml")]
    chosen_scen = st.selectbox("Select Scenario Preset", scen_files, index=0 if scen_files else None)

    if chosen_scen:
        s_path = Path("scenarios") / chosen_scen
        with open(s_path, "r", encoding="utf-8") as f:
            s_dict = yaml.safe_load(f)

        horizon = st.slider("Simulation Horizon (Days)", 15, 180, int(s_dict.get("horizon_days", 90)))
        st.subheader("Configured Interventions")
        st.dataframe(pd.DataFrame(s_dict.get("interventions", [])))

        st.subheader("Optimization Targets")
        st.json(s_dict.get("objectives", {}))

# --- STEP 5: SIMULATION ENGINE ---
elif step == "5. Simulation Engine":
    st.header("Step 5: Run Outbreak Simulation")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        run_horizon = st.number_input("Horizon (days)", value=45, min_value=10, max_value=180)
        run_seed = st.number_input("Random Seed", value=42, min_value=1)
    with col_s2:
        d_choice = st.selectbox("Active Disease", [f.name for f in Path("diseases").glob("*.yaml")])
        s_choice = st.selectbox("Active Scenario", [f.name for f in Path("scenarios").glob("*.yaml")])

    if st.button("🚀 Execute Outbreak Simulation"):
        if st.session_state.pop_soa is None:
            st.session_state.pop_soa = build_synthetic_population(
                st.session_state.region_dir,
                scale_agents=st.session_state.pop_scale,
                random_seed=run_seed
            )

        with open(Path("diseases") / d_choice, "r", encoding="utf-8") as f:
            d_pack = DiseasePack(**yaml.safe_load(f))
        with open(Path("scenarios") / s_choice, "r", encoding="utf-8") as f:
            s_data = yaml.safe_load(f)
            s_data["horizon_days"] = int(run_horizon)
            s_data["random_seed"] = int(run_seed)
            s_pack = ScenarioPack(**s_data)

        with st.spinner("Stepping through epidemic progression day by day..."):
            res = run_simulation(st.session_state.pop_soa, d_pack, s_pack)
            st.session_state.sim_results = res
            st.success("Simulation finished!")

    if st.session_state.sim_results:
        res = st.session_state.sim_results
        st.text(res.summary_table())

        # Plotly state curves
        df_curves = pd.DataFrame(res.daily_state_counts, columns=res.state_names)
        df_curves["day"] = np.arange(len(df_curves))
        fig = px.line(df_curves, x="day", y=res.state_names, title="Epidemic Compartment Dynamics (State Trajectories)")
        st.plotly_chart(fig, use_container_width=True)

# --- STEP 6: ANALYSIS & EQUITY ---
elif step == "6. Analysis & Equity":
    st.header("Step 6: Analysis, Equity Audit, and Spatial Spread Matrix")
    if not st.session_state.sim_results:
        st.warning("Please run a simulation in Step 5 first.")
    else:
        res = st.session_state.sim_results
        pop = st.session_state.pop_soa

        tab_eq, tab_spread = st.tabs(["Equity & Disparities", "Spatial Spread Matrix"])

        with tab_eq:
            eq = evaluate_equity(pop, res)
            st.text(eq.summary())
            df_eq = pd.DataFrame(list(eq.area_attack_rates.items()), columns=["Area", "Attack_Rate"])
            fig_eq = px.bar(df_eq, x="Area", y="Attack_Rate", color="Attack_Rate", title="Attack Rate by Administrative Area")
            st.plotly_chart(fig_eq, use_container_width=True)

        with tab_spread:
            if st.button("Compute Spatial Spread Matrix"):
                with st.spinner("Computing arrival delays across all areas..."):
                    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
                        dp = DiseasePack(**yaml.safe_load(f))
                    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
                        sc = ScenarioPack(**yaml.safe_load(f))
                    sm = compute_spread_matrix(pop, dp, sc, n_seeds=2, max_days=30)
                    st.dataframe(sm.to_dataframe())
                    fig_sm = px.imshow(sm.mean_arrival_days, x=sm.area_names, y=sm.area_names, title="Mean Days Until First Infection Arrival", labels=dict(color="Days"))
                    st.plotly_chart(fig_sm, use_container_width=True)

# --- STEP 7: POLICY ADVISOR & OPTIMIZER ---
elif step == "7. Policy Advisor & Optimizer":
    st.header("Step 7: Autonomous Policy Advisor & NSGA-II Optimizer")
    tab_adv, tab_opt = st.tabs(["Advisor Agent", "Optuna NSGA-II Pareto Front"])

    with tab_adv:
        st.subheader("Autonomous Policy Advisor")
        st.caption("Loops through baseline evaluation, vulnerability identification, and counterfactual testing.")
        if st.button("Run Advisor Agent"):
            if st.session_state.pop_soa is None:
                st.session_state.pop_soa = build_synthetic_population(st.session_state.region_dir, scale_agents=3000)
            with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
                dp = DiseasePack(**yaml.safe_load(f))
            with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
                sc = ScenarioPack(**yaml.safe_load(f))

            toolkit = AdvisorToolKit(st.session_state.pop_soa, dp, sc)
            advisor = AdvisorAgent(toolkit, run_budget=4)
            with st.spinner("Advisor exploring counterfactual policy interventions..."):
                rec = advisor.run_advisory_loop()
                st.success("Advisory Recommendation Formulated!")
                st.json(rec.model_dump())

    with tab_opt:
        st.subheader("Multi-Objective NSGA-II Frontier")
        if st.button("Search Optimal Policy Trade-offs"):
            if st.session_state.pop_soa is None:
                st.session_state.pop_soa = build_synthetic_population(st.session_state.region_dir, scale_agents=3000)
            with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
                dp = DiseasePack(**yaml.safe_load(f))
            with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
                sc = ScenarioPack(**yaml.safe_load(f))

            with st.spinner("Exploring Pareto front with Optuna NSGA-II..."):
                pareto_df = run_optuna_search(st.session_state.pop_soa, dp, sc, n_trials=8)
                st.dataframe(pareto_df)
                if not pareto_df.empty:
                    fig_p = px.scatter(pareto_df, x="deaths", y="cost", size="peak_icu", color="deaths", title="Pareto Trade-off: Fatalities vs Economic Cost")
                    st.plotly_chart(fig_p, use_container_width=True)

# --- STEP 8: EXPORT AUDIT REPORT ---
elif step == "8. Export Audit Report":
    st.header("Step 8: Export Provenance and Audit Report")
    st.write("Generates a compliance report containing model provenance, assumptions, and counterfactual results.")

    report_html = f"""
    <html>
    <head><title>EpiSwarm Simulation Audit Report</title></head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
    <h1>EpiSwarm Studio Audit Report</h1>
    <p><b>Status:</b> UNCALIBRATED (Counterfactual Model Exploration)</p>
    <p><b>Region:</b> {st.session_state.region_dir.name}</p>
    <p><b>Agents Simulated:</b> {st.session_state.pop_scale:,}</p>
    <h2>Model Honesty & Provenance</h2>
    <ul>
        <li>Behavior layer decisions are unvalidated for empirical fidelity.</li>
        <li>Synthetic fixtures are designated for test benchmarking only.</li>
        <li>Hospital overflow reflects stated capacity thresholds.</li>
    </ul>
    <h2>Core Methodology References</h2>
    <p>Libin et al. (2020) <i>Deep reinforcement learning for large-scale epidemic control</i> (arXiv:2003.13676v1)</p>
    <p>Prem et al. (2021) <i>Projecting social contact matrices in 152 countries</i></p>
    </body>
    </html>
    """
    st.download_button(
        label="📥 Download Audit Report (HTML)",
        data=report_html,
        file_name="episwarm_audit_report.html",
        mime="text/html"
    )

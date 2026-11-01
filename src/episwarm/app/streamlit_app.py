"""EpiSwarm Studio: Interactive Outbreak Simulation & Policy Advisory App (Streamlit + Plotly)."""

import os
import time
from pathlib import Path
import yaml
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from episwarm.packs.region import RegionPack, RegionMeta, L0QuickInputs
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction, SeedingConfig, ResourceAddAction
from episwarm.packs.behavior import BehaviorPack, RumorTopic, RumorBehaviorEffects, ComplianceWeights
from episwarm.importers.quick_region import QuickRegionBuilder
from episwarm.importers.mapper import ColumnMapper
from episwarm.population.build import build_synthetic_population, PopulationSoA
from episwarm.engine.sim import run_simulation
from episwarm.engine.healthcare import RegionalHealthcareSystem
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.advisor.agent import AdvisorAgent
from episwarm.optimize.search import run_optuna_search
from episwarm.analysis.equity import evaluate_equity
from episwarm.analysis.spread_matrix import compute_spread_matrix
from episwarm.analysis.metrics import evaluate_single_run_objectives
from episwarm.analysis.calibration import calibrate_to_observed_data
from episwarm.analysis.marginal_value import compute_marginal_value_curve, rank_areas_by_marginal_benefit
from episwarm.analysis.resource_whatif import evaluate_resource_whatif_paired

# Page config
st.set_page_config(
    page_title="EpiSwarm Studio",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
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
if "selected_agent_id" not in st.session_state:
    st.session_state.selected_agent_id = 0
if "gemini_key_input" not in st.session_state:
    st.session_state.gemini_key_input = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
if "gemini_model_input" not in st.session_state:
    st.session_state.gemini_model_input = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

# Helper for testing Gemini connectivity
def ping_gemini(api_key: str, model_name: str) -> dict:
    if not api_key:
        return {"status": "FAIL", "msg": "API Key is empty."}
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
    try:
        t0 = time.perf_counter()
        resp = requests.post(
            url,
            json={"contents": [{"parts": [{"text": "ping"}]}]},
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        dt = round((time.perf_counter() - t0) * 1000, 1)
        if resp.status_code == 200:
            return {"status": "OK", "latency_ms": dt, "msg": f"Connected to {model_name} ({dt} ms)"}
        else:
            err = resp.json().get("error", {}).get("message", resp.text[:120])
            return {"status": "FAIL", "msg": f"HTTP {resp.status_code}: {err}"}
    except Exception as e:
        return {"status": "FAIL", "msg": str(e)}

# Persistent Title & Honesty Banners
st.title("🧬 EpiSwarm Studio")
st.caption("Configurable Agent-Based Outbreak Simulation & Multi-Objective Response Planning")

col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    st.warning("⚠️ UNCALIBRATED: Run comparisons are counterfactual under stated assumptions, not forecasts.")
with col_b2:
    st.info(f"ℹ️ ACTIVE REGION: `{st.session_state.region_dir.name}` (Synthetic Fixture)")
with col_b3:
    st.error("🛡️ BEHAVIOR LAYER UNVALIDATED: LLM-driven compliance is hypothetical.")

# Sidebar Navigation & Settings
st.sidebar.header("Studio Mode")
studio_mode = st.sidebar.radio(
    "Active Mode",
    ["Simulate (Exploration)", "Plan (Advisory & Optimization)"],
    index=0
)

# Gemini API Configuration Box in Sidebar
with st.sidebar.expander("🔑 Gemini API Settings", expanded=False):
    st.caption("Configure Google Gemini for LLM policy decisions & autonomous advisor agent.")
    gem_key = st.text_input("Gemini API Key", value=st.session_state.gemini_key_input, type="password")
    gem_model = st.selectbox(
        "Gemini Model",
        ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-pro-latest"],
        index=0 if st.session_state.gemini_model_input not in ["gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-pro-latest"] else ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-pro-latest"].index(st.session_state.gemini_model_input)
    )
    if st.button("⚡ Test Gemini Connectivity"):
        with st.spinner("Pinging Gemini API..."):
            res_ping = ping_gemini(gem_key, gem_model)
            if res_ping["status"] == "OK":
                st.success(res_ping["msg"])
                st.session_state.gemini_key_input = gem_key
                st.session_state.gemini_model_input = gem_model
                os.environ["GEMINI_API_KEY"] = gem_key
                os.environ["GEMINI_MODEL"] = gem_model
            else:
                st.error(res_ping["msg"])

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

# --- STEP 1: REGION & POPULATION ---
if step == "1. Region & Population":
    st.header("Step 1: Region & Synthetic Population Builder")
    tab_preset, tab_l0, tab_upload = st.tabs(["Pre-configured Packs", "Quick Region (L0) Builder", "Upload & Column Mapper"])

    with tab_preset:
        pack_choices = [p.name for p in Path("regions").iterdir() if p.is_dir() and not p.name.startswith(".")]
        curr_idx = pack_choices.index(st.session_state.region_dir.name) if st.session_state.region_dir.name in pack_choices else 0
        chosen = st.selectbox("Select Region Pack", pack_choices, index=curr_idx)
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
    st.subheader("Generate Synthetic Resident Population (Structure-of-Arrays)")
    col_sc1, col_sc2 = st.columns([2, 1])
    with col_sc1:
        st.session_state.pop_scale = st.select_slider("Simulation Agent Scale", options=[2500, 5000, 10000, 25000, 50000], value=st.session_state.pop_scale if st.session_state.pop_scale in [2500, 5000, 10000, 25000, 50000] else 5000)
    with col_sc2:
        if st.button("Build Synthetic Population", type="primary"):
            with st.spinner("Synthesizing population via Structure-of-Arrays (SoA) and IPF..."):
                pop = build_synthetic_population(
                    st.session_state.region_dir,
                    scale_agents=st.session_state.pop_scale,
                    random_seed=42
                )
                st.session_state.pop_soa = pop
                st.session_state.selected_agent_id = 0
                st.success(f"Instantiated {pop.n_agents:,} synthetic agents!")

    # BROWSE ALL AGENTS (Interactive Explorer & Detailed Dossier)
    if st.session_state.pop_soa is not None:
        pop = st.session_state.pop_soa
        st.divider()
        st.subheader("👥 Resident Population Explorer (Browse All Agents)")
        st.caption(f"Explore and inspect any of the {pop.n_agents:,} synthetic agents in the active population.")

        # Population Key Metrics
        km1, km2, km3, km4 = st.columns(4)
        with km1:
            st.metric("Total Simulated Agents", f"{pop.n_agents:,}")
        with km2:
            st.metric("Unique Households", f"{len(np.unique(pop.household_id)):,}")
        with km3:
            st.metric("Mean Population Age", f"{float(np.mean(pop.age)):.1f} yrs")
        with km4:
            st.metric("Gender Ratio", f"{float(np.mean(pop.sex)*100):.1f}% F / {100-float(np.mean(pop.sex)*100):.1f}% M")

        role_labels = {0: "Child/Dependent", 1: "Primary Earner", 2: "Caregiver Adult", 3: "Elder Resident"}
        routine_labels = {
            0: "Student / Youth",
            1: "Office / Commercial",
            2: "Shift / Industrial",
            3: "Informal Market",
            4: "Homemaker",
            5: "Retired / Home"
        }
        income_labels = {0: "Low", 1: "Middle", 2: "High"}

        # Filters for exploring agents
        with st.expander("🔍 Filter Resident Population", expanded=False):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                area_names = ["ALL"] + sorted([str(pop.int_to_area_id.get(aid, aid)) for aid in np.unique(pop.area_id)])
                selected_area = st.selectbox("Filter by Area", area_names, index=0)
            with f_col2:
                age_range = st.slider("Filter by Age Range", 0, 100, (0, 100))
            with f_col3:
                role_opts = ["ALL"] + list(role_labels.values())
                selected_role = st.selectbox("Filter by Household Role", role_opts, index=0)

        # Build filtered dataframe indices
        mask = (pop.age >= age_range[0]) & (pop.age <= age_range[1])
        if selected_area != "ALL":
            target_aid = [k for k, v in pop.int_to_area_id.items() if str(v) == selected_area]
            if target_aid:
                mask = mask & (pop.area_id == target_aid[0])
        if selected_role != "ALL":
            target_role = [k for k, v in role_labels.items() if v == selected_role]
            if target_role:
                mask = mask & (pop.household_role == target_role[0])

        matching_indices = np.where(mask)[0]
        st.write(f"**Found {len(matching_indices):,} matching agents** (showing interactive table below):")

        # Interactive selection table (paginated slice)
        page_size = 50
        max_page = max(1, (len(matching_indices) + page_size - 1) // page_size)
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            page_num = st.number_input("Table Page", min_value=1, max_value=max_page, value=1)
        with col_p2:
            agent_direct = st.number_input(
                "Direct Inspect: Enter any Agent ID",
                min_value=0,
                max_value=pop.n_agents - 1,
                value=int(st.session_state.selected_agent_id)
            )
            if agent_direct != st.session_state.selected_agent_id:
                st.session_state.selected_agent_id = int(agent_direct)

        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(matching_indices))
        slice_indices = matching_indices[start_idx:end_idx]

        df_table = pd.DataFrame({
            "Agent ID": pop.agent_id[slice_indices],
            "Area": [pop.int_to_area_id.get(aid, str(aid)) for aid in pop.area_id[slice_indices]],
            "Age": pop.age[slice_indices],
            "Sex": ["Female" if s == 1 else "Male" for s in pop.sex[slice_indices]],
            "Household ID": pop.household_id[slice_indices],
            "Role": [role_labels.get(r, "Member") for r in pop.household_role[slice_indices]],
            "Routine": [routine_labels.get(rt, "General") for rt in pop.routine_template[slice_indices]],
            "Income Band": [income_labels.get(inc, "Middle") for inc in pop.income_band[slice_indices]],
            "Compliance": np.round(pop.compliance[slice_indices], 2),
            "Trust": np.round(pop.trust[slice_indices], 2),
            "Rumor Susceptibility": np.round(pop.rumor_susceptibility[slice_indices], 2)
        })

        event = st.dataframe(
            df_table,
            width="stretch",
            selection_mode="single-row",
            on_select="rerun"
        )
        if event and event.selection and event.selection.rows:
            sel_row = event.selection.rows[0]
            st.session_state.selected_agent_id = int(df_table.iloc[sel_row]["Agent ID"])

        # Display Selected Agent Detailed Dossier Card
        inspect_id = int(st.session_state.selected_agent_id)
        if 0 <= inspect_id < pop.n_agents:
            prof = pop.get_showcase_profile(inspect_id)
            st.markdown(f"### 🪪 Detailed Dossier: Agent #{prof['agent_id']}")
            
            d_col1, d_col2, d_col3, d_col4 = st.columns(4)
            with d_col1:
                st.markdown(f"**Demographics**")
                st.write(f"- **Age:** {prof['age']} years")
                st.write(f"- **Sex:** {prof['sex']}")
                st.write(f"- **Area:** `{prof['area']}`")
                st.write(f"- **Role:** {prof['role']}")
            with d_col2:
                st.markdown(f"**Socioeconomic**")
                st.write(f"- **Routine:** {prof['routine']}")
                st.write(f"- **Income Tier:** {prof['income_band']}")
                st.write(f"- **Buffer Score:** {prof['financial_buffer']:.2f}")
                st.write(f"- **Caregiver:** {'Yes' if prof['caregiver'] else 'No'}")
            with d_col3:
                st.markdown(f"**Healthcare Baseline**")
                st.write(f"- **Self-Care Score:** {prof['self_care']:.2f}")
                st.write(f"- **Support Score:** {prof['support']:.2f}")
                st.write(f"- **Alt Care Access:** {prof['alt_care_access']:.2f}")
                st.write(f"- **Past Bereavement:** {'Yes' if prof['past_bereavement'] else 'No'}")
            with d_col4:
                st.markdown(f"**Behavioral Traits**")
                st.write(f"- **Compliance:** {prof['compliance']:.2f}")
                st.write(f"- **Institutional Trust:** {float(pop.trust[inspect_id]):.2f}")
                st.write(f"- **Rumor Susceptibility:** {float(pop.rumor_susceptibility[inspect_id]):.2f}")
                st.write(f"- **Risk Tolerance:** {float(pop.risk_tolerance[inspect_id]):.2f}")

            st.info(prof["narrative"])

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
        st.dataframe(pd.DataFrame(d_dict.get("states", [])), width="stretch")

        st.subheader("State Transitions")
        st.dataframe(pd.DataFrame(d_dict.get("transitions", [])), width="stretch")

# --- STEP 3: HEALTHCARE & CAPACITY ---
elif step == "3. Healthcare & Capacity":
    st.header("Step 3: Regional Resources and Healthcare Capacity")
    res_file = st.session_state.region_dir / "resources.csv"
    cap_file = st.session_state.region_dir / "capacity.csv"

    if res_file.exists():
        res_df = pd.read_csv(res_file)
        st.dataframe(res_df, width="stretch")
        fig = px.bar(res_df, x="resource_id", y="nominal", color="area_id", barmode="group", title="Nominal Generic Resources by Area")
        st.plotly_chart(fig, width="stretch")
    elif cap_file.exists():
        cap_df = pd.read_csv(cap_file)
        st.dataframe(cap_df, width="stretch")
        fig = px.bar(cap_df, x="hospital_id", y="nominal", color="category", barmode="group", title="Nominal Capacity by Facility")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No resources.csv or capacity.csv present. Defaulting to standard generic clinical resources.")

    with st.expander("Add Resources & What-If Capacity Planning (Spec 6.4)", expanded=True):
        st.subheader("What-If Scenario: Provision Extra Clinical Resources")
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            whatif_res = st.text_input("Resource ID", "res_bed")
        with col_w2:
            whatif_area = st.text_input("Target Area ('ALL' or area_id)", "ALL")
        with col_w3:
            whatif_amt = st.number_input("Units to Provision", value=20.0, step=5.0)

        col_wb1, col_wb2 = st.columns(2)
        with col_wb1:
            if st.button("Evaluate Resource What-If (Paired Comparison)"):
                if st.session_state.pop_soa is None:
                    st.session_state.pop_soa = build_synthetic_population(st.session_state.region_dir, scale_agents=st.session_state.pop_scale)
                with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as df:
                    d_pack = DiseasePack(**yaml.safe_load(df))
                with open("scenarios/baseline.yaml", "r", encoding="utf-8") as sf:
                    s_pack = ScenarioPack(**yaml.safe_load(sf))

                action = ResourceAddAction(resource_id=whatif_res, area_id=whatif_area, amount=float(whatif_amt))
                res_df = pd.read_csv(res_file) if res_file.exists() else None

                try:
                    report = evaluate_resource_whatif_paired(
                        st.session_state.pop_soa, d_pack, s_pack, [action], resources_df=res_df, n_paired_seeds=4
                    )
                    st.success("Paired counterfactual evaluation completed!")
                    st.write("#### Paired Delta Comparison (Variant vs Baseline):")
                    st.write(f"- **Deaths Reduction:** {report['deaths_delta']['mean']:.1f} (95% CI: [{report['deaths_delta']['ci_lower']:.1f}, {report['deaths_delta']['ci_upper']:.1f}])")
                    st.write(f"- **Overflow Fatalities Delta:** {report['overflow_deaths_delta']['mean']:.1f}")
                    st.write(f"- **Unmet Demand Delta:** {report['unmet_demand_delta']['mean']:.1f}")
                    st.write(f"- **Disparity Gap Delta:** {report['equity_gap_delta']['mean']*100:.2f}%")
                except ValueError as e:
                    st.error(str(e))

        with col_wb2:
            if st.button("Compute Marginal Value Curve & Best Area"):
                if st.session_state.pop_soa is None:
                    st.session_state.pop_soa = build_synthetic_population(st.session_state.region_dir, scale_agents=st.session_state.pop_scale)
                with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as df:
                    d_pack = DiseasePack(**yaml.safe_load(df))
                with open("scenarios/baseline.yaml", "r", encoding="utf-8") as sf:
                    s_pack = ScenarioPack(**yaml.safe_load(sf))

                m_res = compute_marginal_value_curve(
                    st.session_state.pop_soa, d_pack, s_pack, resource_id=whatif_res, area_id=whatif_area, step_units=10.0, max_units=40.0, n_paired_seeds=3
                )
                ranking = rank_areas_by_marginal_benefit(
                    st.session_state.pop_soa, d_pack, s_pack, resource_id=whatif_res, test_units=15.0, n_paired_seeds=3
                )
                df_mv = pd.DataFrame([{"units": p.units_added, "deaths": p.mean_deaths, "marginal_benefit": p.marginal_death_reduction} for p in m_res.curve])
                fig_mv = px.line(df_mv, x="units", y="marginal_benefit", title="Marginal Value Curve (Diminishing Returns)")
                st.plotly_chart(fig_mv, width="stretch")
                st.write(f"**Diminishing Returns Threshold:** ~{m_res.diminishing_returns_threshold_units:.0f} units")
                st.write(f"**Best Area Ranking for Next Unit:** {ranking}")

# --- STEP 4: INTERVENTIONS & SCENARIO ---
elif step == "4. Interventions & Scenario":
    st.header("Step 4: Non-Pharmaceutical Interventions, Scenarios & Behaviors")
    scen_files = [f.name for f in Path("scenarios").glob("*.yaml")]
    chosen_scen = st.selectbox("Select Scenario Preset", scen_files, index=0 if scen_files else None)

    if chosen_scen:
        s_path = Path("scenarios") / chosen_scen
        with open(s_path, "r", encoding="utf-8") as f:
            s_dict = yaml.safe_load(f)

        horizon = st.slider("Simulation Horizon (Days)", 15, 180, int(s_dict.get("horizon_days", 90)))
        st.subheader("Configured Interventions")
        st.dataframe(pd.DataFrame(s_dict.get("interventions", [])), width="stretch")

        st.subheader("Optimization Targets")
        st.json(s_dict.get("objectives", {}))

    st.divider()
    st.subheader("Behavioral Presets & Misinformation Dynamics")
    beh_files = [f.name for f in Path("behavior").glob("*.yaml")]
    chosen_beh = st.selectbox("Select Behavior Preset", beh_files, index=0 if beh_files else None)
    if chosen_beh:
        b_path = Path("behavior") / chosen_beh
        with open(b_path, "r", encoding="utf-8") as bf:
            b_dict = yaml.safe_load(bf)
        st.caption(f"Context: {b_dict.get('context', '')}")
        st.write("Active Misinformation Topics:")
        st.dataframe(pd.DataFrame(b_dict.get("rumor_topics", [])), width="stretch")
        st.write("Dynamic Compliance Weights:")
        st.json(b_dict.get("compliance_weights", {}))

# --- STEP 5: SIMULATION ENGINE (MODULAR INDEPENDENT SETUP) ---
elif step == "5. Simulation Engine":
    st.header("Step 5: Modular Simulation Setup & Execution")
    st.caption("Configure Region, Disease, Scenario, and Behavior modules independently before executing the simulation.")

    mod1, mod2 = st.columns(2)

    # MODULE 1: REGION
    with mod1:
        st.markdown("### 📍 Module 1: Region & Population")
        reg_choices = [p.name for p in Path("regions").iterdir() if p.is_dir() and not p.name.startswith(".")]
        sim_reg = st.selectbox(
            "Region Preset",
            reg_choices,
            index=reg_choices.index(st.session_state.region_dir.name) if st.session_state.region_dir.name in reg_choices else 0,
            key="sim_mod_region"
        )
        st.session_state.region_dir = Path("regions") / sim_reg
        sim_scale = st.select_slider(
            "Population Scale",
            options=[2500, 5000, 10000, 25000, 50000],
            value=st.session_state.pop_scale if st.session_state.pop_scale in [2500, 5000, 10000, 25000, 50000] else 5000,
            key="sim_mod_scale"
        )
        st.session_state.pop_scale = sim_scale

    # MODULE 2: DISEASE
    with mod2:
        st.markdown("### 🦠 Module 2: Disease Transmission")
        d_files = [f.name for f in Path("diseases").glob("*.yaml")]
        sim_d_choice = st.selectbox("Disease Preset", d_files, index=0, key="sim_mod_disease")
        with open(Path("diseases") / sim_d_choice, "r", encoding="utf-8") as f:
            d_raw = yaml.safe_load(f)
        
        col_dr1, col_dr2 = st.columns(2)
        with col_dr1:
            sim_r0 = st.number_input("R0 Override", value=float(d_raw.get("transmission", {}).get("r0", 2.5)), step=0.1)
        with col_dr2:
            sim_k = st.number_input("Overdispersion k", value=float(d_raw.get("transmission", {}).get("overdispersion_k", 0.16)), step=0.02)

    mod3, mod4 = st.columns(2)

    # MODULE 3: SCENARIO & INTERVENTIONS
    with mod3:
        st.markdown("### 🏛️ Module 3: Scenario & Interventions")
        s_files = [f.name for f in Path("scenarios").glob("*.yaml")]
        sim_s_choice = st.selectbox("Scenario Preset", s_files, index=0, key="sim_mod_scenario")
        with open(Path("scenarios") / sim_s_choice, "r", encoding="utf-8") as f:
            s_raw = yaml.safe_load(f)

        col_sr1, col_sr2 = st.columns(2)
        with col_sr1:
            sim_horizon = st.number_input("Horizon (Days)", value=int(s_raw.get("horizon_days", 60)), min_value=15, max_value=180)
        with col_sr2:
            sim_seed = st.number_input("Random Seed", value=int(s_raw.get("random_seed", 42)), min_value=1)

        sim_mask_toggle = st.checkbox("Enforce Universal Mask Mandate", value=any(i.get("measure_type") == "mask_mandate" for i in s_raw.get("interventions", [])))
        sim_school_toggle = st.checkbox("Enforce School Closure", value=any(i.get("measure_type") == "school_closure" for i in s_raw.get("interventions", [])))
        sim_curfew_toggle = st.checkbox("Enforce Movement / Curfew Restrictions", value=any(i.get("measure_type") == "curfew" for i in s_raw.get("interventions", [])))

    # MODULE 4: BEHAVIOR & RUMORS
    with mod4:
        st.markdown("### 🧠 Module 4: Behavior & Misinformation")
        b_files = [f.name for f in Path("behavior").glob("*.yaml")]
        sim_b_choice = st.selectbox("Behavior Preset", b_files, index=0, key="sim_mod_behavior")
        with open(Path("behavior") / sim_b_choice, "r", encoding="utf-8") as f:
            b_raw = yaml.safe_load(f)

        sim_rumor_rate = st.slider("Rumor Spread Rate", 0.01, 0.20, float(b_raw.get("rumor_spread_rate", 0.05)), step=0.01)
        sim_policy_backend = st.selectbox(
            "Behavior Policy Engine",
            ["Deterministic Rules (RulePolicy - Fast)", "Google Gemini LLM (gemini-3.5-flash)", "Local LLM (Ollama)"],
            index=0
        )
        if "Gemini" in sim_policy_backend:
            curr_gem_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
            if curr_gem_key:
                st.caption(f"✅ Gemini configured (Model: `{os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')}`)")
            else:
                st.warning("⚠️ GEMINI_API_KEY not configured. Set it in sidebar or .env.")

    st.divider()

    # EXECUTE SIMULATION BUTTON
    if st.button("🚀 Execute Outbreak Simulation", type="primary"):
        # 1. Build or re-use PopulationSoA
        with st.spinner("Synthesizing population Structure-of-Arrays (SoA)..."):
            pop = build_synthetic_population(
                st.session_state.region_dir,
                scale_agents=int(sim_scale),
                random_seed=int(sim_seed)
            )
            st.session_state.pop_soa = pop

        # 2. Compile DiseasePack with overrides
        d_raw["transmission"]["r0"] = float(sim_r0)
        d_raw["transmission"]["overdispersion_k"] = float(sim_k)
        d_pack = DiseasePack(**d_raw)

        # 3. Compile ScenarioPack with overrides & active toggles
        s_raw["horizon_days"] = int(sim_horizon)
        s_raw["random_seed"] = int(sim_seed)
        active_interventions = []
        if sim_mask_toggle:
            active_interventions.append(InterventionAction(
                name="universal_mask_mandate",
                measure_type="mask_mandate",
                area_id="ALL",
                start_day=5,
                end_day=sim_horizon,
                stringency=0.75,
                cost_per_day=0.5
            ))
        if sim_school_toggle:
            active_interventions.append(InterventionAction(
                name="targeted_school_closure",
                measure_type="school_closure",
                area_id="ALL",
                start_day=8,
                end_day=min(45, sim_horizon),
                stringency=0.90,
                cost_per_day=1.5
            ))
        if sim_curfew_toggle:
            active_interventions.append(InterventionAction(
                name="movement_curfew",
                measure_type="curfew",
                area_id="ALL",
                start_day=10,
                end_day=sim_horizon,
                stringency=0.65,
                cost_per_day=1.0
            ))
        s_raw["interventions"] = active_interventions
        s_pack = ScenarioPack(**s_raw)

        # 4. Compile BehaviorPack with overrides
        b_raw["rumor_spread_rate"] = float(sim_rumor_rate)
        b_pack = BehaviorPack(**b_raw)

        # 5. Resolve policy engine
        policy_inst = None
        if "Gemini" in sim_policy_backend:
            from episwarm.behavior.policy_gemini import GeminiPolicy
            policy_inst = GeminiPolicy()
        elif "Local" in sim_policy_backend:
            from episwarm.behavior.policy_local import LocalLLMPolicy
            policy_inst = LocalLLMPolicy()

        # 6. Run simulation
        with st.spinner(f"Stepping through {sim_horizon} days of epidemic propagation with {sim_policy_backend.split(' ')[0]}..."):
            res = run_simulation(
                pop,
                d_pack,
                s_pack,
                behavior_pack=b_pack,
                policy=policy_inst
            )
            st.session_state.sim_results = res
            st.success(f"Simulation completed across {sim_horizon} days for {pop.n_agents:,} synthetic agents!")

    # SIMULATION RESULTS DASHBOARD
    if st.session_state.sim_results:
        res = st.session_state.sim_results
        st.markdown("### 📊 Simulation Telemetry & Epidemic Progression")

        # Top KPI Cards
        state_idx = {name: i for i, name in enumerate(res.state_names)}
        daily_i = res.daily_state_counts[:, state_idx.get("I", 2)]
        daily_d = res.daily_state_counts[:, state_idx.get("D", -1)] if "D" in state_idx else np.zeros(len(res.daily_state_counts))
        daily_icu = res.daily_state_counts[:, state_idx.get("ICU", -1)] if "ICU" in state_idx else np.zeros(len(res.daily_state_counts))
        daily_h = res.daily_state_counts[:, state_idx.get("H", -1)] if "H" in state_idx else np.zeros(len(res.daily_state_counts))

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1:
            st.metric("Peak Active Cases", f"{int(np.max(daily_i)):,}")
        with k2:
            st.metric("Total Fatalities", f"{int(daily_d[-1]):,}")
        with k3:
            st.metric("Peak ICU Demand", f"{int(np.max(daily_icu)):,}")
        with k4:
            st.metric("Total Hospitalized", f"{int(np.max(daily_h)):,}")
        with k5:
            final_comp = float(res.daily_mean_compliance[-1]) if res.daily_mean_compliance is not None else 0.70
            st.metric("Mean Compliance", f"{final_comp*100:.1f}%")
        with k6:
            peak_rumor = 0.0
            if res.daily_rumor_beliefs:
                peak_rumor = max([max(v) for v in res.daily_rumor_beliefs.values()])
            st.metric("Peak Rumor Belief", f"{peak_rumor*100:.1f}%")

        # State Curves (SEIR Dynamics)
        df_curves = pd.DataFrame(res.daily_state_counts, columns=res.state_names)
        df_curves["day"] = np.arange(len(df_curves))
        fig = px.line(df_curves, x="day", y=res.state_names, title="Epidemic Compartment Dynamics (Daily State Trajectories)")
        st.plotly_chart(fig, width="stretch")

        # Behavior & Misinformation Dynamics
        if res.daily_mean_compliance is not None or res.daily_rumor_beliefs:
            cb1, cb2 = st.columns(2)
            with cb1:
                if res.daily_mean_compliance is not None:
                    df_comp = pd.DataFrame({"day": np.arange(len(res.daily_mean_compliance)), "compliance": res.daily_mean_compliance})
                    fig_comp = px.line(df_comp, x="day", y="compliance", title="Public Policy Compliance Over Time (with Fatigue & Norms)")
                    st.plotly_chart(fig_comp, width="stretch")
            with cb2:
                if res.daily_rumor_beliefs:
                    df_rumor = pd.DataFrame(res.daily_rumor_beliefs)
                    df_rumor["day"] = np.arange(len(df_rumor))
                    fig_rumor = px.line(df_rumor, x="day", y=list(res.daily_rumor_beliefs.keys()), title="Mean Rumor Belief Over Time (Dynamic Fluctuation & Decay)")
                    st.plotly_chart(fig_rumor, width="stretch")

        with st.expander("Summary Table (Daily Snapshot Counts)", expanded=False):
            st.text(res.summary_table())

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
            st.plotly_chart(fig_eq, width="stretch")

        with tab_spread:
            if st.button("Compute Spatial Spread Matrix"):
                with st.spinner("Computing arrival delays across all areas..."):
                    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
                        dp = DiseasePack(**yaml.safe_load(f))
                    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
                        sc = ScenarioPack(**yaml.safe_load(f))
                    sm = compute_spread_matrix(pop, dp, sc, n_seeds=2, max_days=30)
                    st.dataframe(sm.to_dataframe(), width="stretch")
                    fig_sm = px.imshow(sm.mean_arrival_days, x=sm.area_names, y=sm.area_names, title="Mean Days Until First Infection Arrival", labels=dict(color="Days"))
                    st.plotly_chart(fig_sm, width="stretch")

# --- STEP 7: POLICY ADVISOR & OPTIMIZER ---
elif step == "7. Policy Advisor & Optimizer":
    st.header("Step 7: Autonomous Policy Advisor & NSGA-II Optimizer")
    if "Simulate" in studio_mode:
        st.info("ℹ️ Currently in Simulate Mode. The Autonomous Advisor is primary in Plan Mode. Switch to 'Plan (Advisory & Optimization)' in the sidebar for focused decision support.")

    tab_adv, tab_opt = st.tabs(["Advisor Agent", "Optuna NSGA-II Pareto Front"])

    with tab_adv:
        st.subheader("Autonomous Policy Advisor")
        st.caption("Loops through baseline evaluation, vulnerability identification, and counterfactual testing using Gemini Function Calling.")
        
        curr_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        if curr_key:
            st.success(f"Google GenAI Client Ready (Model: `{os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')}`)")
        else:
            st.warning("GEMINI_API_KEY not configured. Advisor will use deterministic heuristic fallback.")

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
                st.dataframe(pareto_df, width="stretch")
                if not pareto_df.empty:
                    fig_p = px.scatter(pareto_df, x="deaths", y="cost", size="peak_icu", color="deaths", title="Pareto Trade-off: Fatalities vs Economic Cost")
                    st.plotly_chart(fig_p, width="stretch")

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

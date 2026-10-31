"""End-to-end interactive demo running EpiSwarm Studio pipeline on synthetic region data."""

import time
import yaml
from pathlib import Path
import numpy as np

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.analysis.equity import evaluate_equity
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.advisor.agent import AdvisorAgent


def main():
    print("======================================================================")
    print("             EpiSwarm Studio: End-to-End Walkthrough Demo             ")
    print("======================================================================")

    print("\nStep 1: Ingesting Synthetic Region Data...")
    print("  -> Loading 'regions/example_synthetic' (5 areas, synthetic hospitals & venues)")
    t0 = time.perf_counter()
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=42)
    t_pop = time.perf_counter() - t0
    print(f"  -> Successfully synthesized {pop.n_agents:,} resident agents in {t_pop:.2f}s.")
    print(f"  -> Each agent represents {pop.sampling_ratio:.1f} actual residents in this region.")

    print("\nStep 2: Loading Generic Respiratory Disease Parameters...")
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    print(f"  -> Pathogen: {d_pack.name} (R0 = {d_pack.transmission.r0})")
    print(f"  -> Sourced Anchors: Levin et al. (2020) age-stratified infection fatality ratios.")
    print(f"  -> Unserved Outcome Model (Spec 6.3): base theta_0 = {d_pack.unserved_outcome.theta_0}, theta_care = {d_pack.unserved_outcome.theta_care}.")
    print(f"  -> Declared Vulnerability Factors: {[vf.id for vf in d_pack.vulnerability_factors]}")

    # Showcase structured narrative
    showcase = pop.get_showcase_profile(0)
    print("\n  [Showcase Resident Narrative (Spec 9)]")
    print(f"  {showcase['narrative'].strip()}")

    print("\nStep 3: Running 30-Day Outbreak Simulation...")
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = 30
        s_pack = ScenarioPack(**s_data)

    t1 = time.perf_counter()
    res = run_simulation(pop, d_pack, s_pack)
    t_sim = time.perf_counter() - t1
    print(f"  -> Simulation complete in {t_sim:.2f}s!")
    print(f"  -> Total infections: {res.total_infections:,} ({res.attack_rate*100:.1f}% attack rate).")
    print(f"  -> Total fatalities: {res.total_deaths:,} under clinical resource constraints.")

    print("\nStep 4: Evaluating Fairness and Geographic Disparities...")
    eq = evaluate_equity(pop, res)
    print(f"  -> Hardest hit area: {eq.worst_off_area} ({eq.area_attack_rates.get(eq.worst_off_area, 0.0)*100:.1f}% attack rate).")
    print(f"  -> Least affected area: {eq.best_off_area} ({eq.area_attack_rates.get(eq.best_off_area, 0.0)*100:.1f}% attack rate).")
    print(f"  -> Geographic equity gap: {eq.area_disparity_gap*100:.2f} percentage points.")

    print("\nStep 5: Consulting the Autonomous Policy Advisor...")
    toolkit = AdvisorToolKit(pop, d_pack, s_pack)
    advisor = AdvisorAgent(toolkit, run_budget=3)
    rec = advisor.run_advisory_loop()
    print("  -> Policy Recommendation Formulated:")
    for i, m in enumerate(rec.recommended_measures):
        print(f"     Measure {i+1}: {m.name} (Type: {m.measure_type}, Days {m.start_day}-{m.end_day})")
    if rec.predicted_deaths_reduction:
        print(f"  -> Estimated Fatality Reduction: {rec.predicted_deaths_reduction:.1f}%")

    print("\n======================================================================")
    print("                       HONESTY & PROVENANCE AUDIT                     ")
    print("======================================================================")
    print("Status: UNCALIBRATED (Run for demonstration and counterfactual planning)")
    print("Data Source Flags:")
    print("  - Population & Venues: SYNTHETIC (Artificial test fixture)")
    print("  - Transmission R0: ASSUMED (2.50)")
    print("  - Resource model: GENERIC (Clinical bed, auxiliary support units)")
    print("  - Behavior Layer: UNVALIDATED (Hypothetical public response curve)")
    print("======================================================================\n")


if __name__ == "__main__":
    main()

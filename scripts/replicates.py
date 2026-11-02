"""CLI entrypoint for running parallel paired replicates with statistical intervals (Spec 11 & Phase 17)."""

import argparse
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.analysis.replicates import run_replicates


def main():
    parser = argparse.ArgumentParser(description="Run N parallel simulation replicates with 95% confidence intervals.")
    parser.add_argument("--region", default="regions/example_synthetic", help="Path to region pack directory")
    parser.add_argument("--disease", default="diseases/respiratory_generic.yaml", help="Path to disease pack YAML")
    parser.add_argument("--scenario-a", default="scenarios/baseline.yaml", help="Path to Scenario A YAML")
    parser.add_argument("--scenario-b", default=None, help="Optional Scenario B for paired comparative counterfactual")
    parser.add_argument("--scale", type=int, default=10000, help="Agent population scale")
    parser.add_argument("--replicates", "-n", type=int, default=30, help="Number of replicates (minimum 30)")
    parser.add_argument("--behavior-mode", default="none", choices=["none", "rule", "llm"], help="Behavior engine mode")
    parser.add_argument("--workers", "-w", type=int, default=4, help="Parallel worker threads")
    args = parser.parse_args()

    print(f"Loading environment: {args.scale:,} agents in {args.region}...")
    pop = build_synthetic_population(args.region, scale_agents=args.scale, random_seed=42)

    with open(args.disease, "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open(args.scenario_a, "r", encoding="utf-8") as f:
        s_data_a = yaml.safe_load(f)
        s_data_a["scale_agents"] = args.scale
        sc_a = ScenarioPack(**s_data_a)

    sc_b = None
    if args.scenario_b:
        with open(args.scenario_b, "r", encoding="utf-8") as f:
            s_data_b = yaml.safe_load(f)
            s_data_b["scale_agents"] = args.scale
            sc_b = ScenarioPack(**s_data_b)

    print(f"Executing {args.replicates} replicates (behavior_mode='{args.behavior_mode}') on {args.workers} workers...")
    summary = run_replicates(
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=sc_a,
        n_replicates=args.replicates,
        behavior_mode=args.behavior_mode,
        paired_scenario=sc_b,
        max_workers=args.workers
    )

    print(summary.summary_table())


if __name__ == "__main__":
    main()


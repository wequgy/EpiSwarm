import time, yaml
from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation

d = DiseasePack(**yaml.safe_load(open("diseases/respiratory_generic.yaml", encoding="utf-8")))
for scale in (5000, 50000, 100000):
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=scale, random_seed=42)
    for n_seed in (25, 200):
        s = yaml.safe_load(open("scenarios/baseline.yaml", encoding="utf-8"))
        s["horizon_days"] = 90
        s["seeding"]["initial_cases_per_area"] = n_seed
        s["interventions"] = []
        t = time.perf_counter()
        r = run_simulation(pop, d, ScenarioPack(**s))
        print(f"scale={scale} seeds={n_seed}: attack={r.attack_rate*100:.1f}% "
              f"beta={r.calibrated_beta:.3f} emp_R0={r.empirical_r0:.2f} "
              f"time={time.perf_counter()-t:.1f}s")


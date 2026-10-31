"""Mutation testing harness to verify that test suite catches broken invariants."""

import subprocess
import sys
from pathlib import Path


def run_mutation_check():
    mutations = [
        {
            "name": "1. Population conservation violation",
            "file": Path("src/episwarm/engine/sim.py"),
            "target": "total == pop.n_agents",
            "mutation_target": "assert total == pop.n_agents",
            "code_target": "states[group_mask] = next_st",
            "code_mutated": "states[group_mask] = next_st; states[0] = -1",  # Corrupt state
            "test_cmd": "pytest tests/test_engine_phase2.py -k test_population_conservation_invariant"
        },
        {
            "name": "2. Absorbing state schema invariant violation",
            "file": Path("src/episwarm/packs/disease.py"),
            "code_target": "raise ValueError(f\"Absorbing state '{t.from_state}' cannot have outgoing transitions\")",
            "code_mutated": "pass  # Mutated: disable absorbing outgoing check",
            "test_cmd": "pytest tests/test_packs_phase0.py -k test_disease_pack_rejects_outgoing_from_absorbing"
        },
        {
            "name": "3. Household adult invariant violation",
            "file": Path("src/episwarm/population/households.py"),
            "code_target": "for h_id in range(n_households):\n        adult_idx = adult_indices[h_id]\n        household_ids[adult_idx] = h_id",
            "code_mutated": "# Mutated: skip adult seeding\n    pass",
            "test_cmd": "pytest tests/test_population_phase1.py -k test_household_adult_invariant"
        },
        {
            "name": "4. Generality rule violation (hardcoded place)",
            "file": Path("src/episwarm/packs/schema.py"),
            "code_target": "class ProvenanceRecord(BaseModel):",
            "code_mutated": "class ProvenanceRecord(BaseModel):\n    # Mutation test: bengaluru\n    dummy_place: str = 'bengaluru'",
            "test_cmd": "pytest tests/test_packs_phase0.py -k test_generality_rule"
        },
        {
            "name": "5. Healthcare capacity violation (ignore 0 capacity)",
            "file": Path("src/episwarm/engine/healthcare.py"),
            "code_target": "is_served = np.zeros(n_patients, dtype=bool)",
            "code_mutated": "is_served = np.ones(n_patients, dtype=bool)",  # Pretend all served
            "test_cmd": "pytest tests/test_healthcare_phase3.py -k test_compliance_mortality_benefit_vs_penalty"
        }
    ]

    results = []
    print("=== Running 5 Mutation Sanity Checks ===")

    for m in mutations:
        file_path = m["file"]
        original_content = file_path.read_text(encoding="utf-8")

        if m["code_target"] not in original_content:
            print(f"[FAIL TO SETUP] Could not find target in {file_path}")
            continue

        try:
            # Apply mutation
            mutated_content = original_content.replace(m["code_target"], m["code_mutated"], 1)
            file_path.write_text(mutated_content, encoding="utf-8")

            # Run test
            proc = subprocess.run(
                f"pytest {m['test_cmd'].replace('pytest ', '')}",
                shell=True,
                capture_output=True,
                text=True
            )

            # Test MUST fail (exit code != 0)
            if proc.returncode != 0:
                print(f"[PASSED] {m['name']}: Test correctly caught mutation and FAILED.")
                results.append((m["name"], "CAUGHT (FAILED AS EXPECTED)", True))
            else:
                print(f"[FAILED] {m['name']}: Test PASSED despite mutation! Test is weak.")
                results.append((m["name"], "MISSED (TEST PASSED)", False))

        finally:
            # Revert mutation
            file_path.write_text(original_content, encoding="utf-8")

    all_passed = all(r[2] for r in results)
    print("\nMutation Check Summary:")
    for name, status, ok in results:
        mark = "OK" if ok else "WEAK"
        print(f"  [{mark}] {name} -> {status}")

    return all_passed


if __name__ == "__main__":
    ok = run_mutation_check()
    sys.exit(0 if ok else 1)

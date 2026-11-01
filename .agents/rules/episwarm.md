# EpiSwarm Studio: Workspace Rules (PART A)

## Project identity
EpiSwarm Studio is a configurable framework for outbreak simulation and response planning. A user supplies a region (population, areas, venues, health-system capacity), chooses or defines a disease, defines response measures, and the framework simulates synthetic residents with homes, workplaces, schools or social spaces, health attributes and traits. It compares measures under stated assumptions and recommends which areas to act on first and which measures to take first. It does not predict when the outbreaks happen, but can simulate outbreaks.

## Honesty & Evidence rules (highest priority)
1. **Evidence, not claims**: For every statement of the form "X works", run a command and show its real output (pytest summary line, benchmark table, screenshot or `AppTest` result).
2. **Reproduction rule**: Run the reproduction before and after every fix.
3. **Automated documentation**: Docs and README numbers are generated from real command output, never typed by hand.
4. **Implementation criteria**: No behavior or advisor feature is IMPLEMENTED until it is called from the engine or app and a test shows its effect on outcomes.
5. Never invent data, statistics, URLs, citations or parameter values. If unknown, leave `null` or use an obviously labeled placeholder with `status: assumed`, and list it in `ASSUMPTIONS.md`.
6. Every parameter and every data file carries provenance: `source` (URL or citation) and `status` in {`user_supplied`, `sourced`, `assumed`, `synthetic`}. Every run report and every UI page shows the list of `assumed` and `synthetic` inputs in use.
7. Separate what is verified (tests passed, checked against a source) from what is assumed or untested in every summary.
8. Never claim validation that was not run. Without user-supplied observed data, every report says "UNCALIBRATED".
9. The behavior layer (LLM-driven decisions) is not validated for any region unless the user supplies observed data to validate against. Show a persistent "behavior layer unvalidated for this region" banner by default.
10. Synthetic fixture data exists only to build and test code. Any run using synthetic input shows a SYNTHETIC DATA banner and is never described as a result about a real place.
11. Rumor, misinformation and compliance of the public are in scope and must be modeled.
12. **Zero credential leakage**: Never ask the user to paste API keys into chat, ever. Keys are configured locally through `scripts/setup_keys.py` and stored only in `.env`. Never commit keys, never print or log them.

## Generality rules
1. No region, country, city or disease constants in `src/`. Everything comes from packs (region, disease, behavior, scenario) and config. Add a test that fails if `src/` contains hardcoded place names or disease names.
2. **No resource-specific names in `src/`**: Resources are completely generic (declared in packs). Hardcoded resource names (including `oxygen`, specific drug brands, etc.) are forbidden in `src/`. Add a test that verifies `src/` contains no hardcoded resource-specific strings.
3. Area hierarchy is user-defined (for example ward, zone, city), up to three levels, with names chosen by the user.
4. Disease is a user-editable state graph, not hardcoded compartments.
5. Units and labels come from the region pack metadata. No currency or language assumptions in the engine.

## Engineering rules
1. Python 3.11 on Windows (PowerShell). Use `pathlib` for paths, avoid bash-only commands or Unix-specific assumptions. Multiprocessing must be Windows-safe (`if __name__ == "__main__":` with picklable top-level functions).
2. Agents are structure-of-arrays (one NumPy array per field). No per-agent Python objects, no Mesa.
3. Infection is computed per venue layer with `numpy.bincount` (infectious load per venue divided by venue size), not pairwise contact lists. Use Numba only after profiling.
4. All randomness flows from one seeded `numpy.random.Generator`. Same packs plus config plus seed must reproduce results exactly.
5. All inputs validated with pydantic and a data-contract validator. No magic numbers in code.
6. Every run writes a manifest (git hash, pack hashes, seed, timestamps, list of assumed or synthetic inputs).
7. Target machine: 16 GB RAM, Core i5, RTX GPU. Peak memory under about 11 GB. Per-agent daily history is allowed for simulating spread; log aggregates by area, age band and health state plus state-change events to disk.
8. pytest for every module, with invariants: population conserved, no negative counts, absorbing states stay absorbing, same seed reproduces results.
9. Secrets only in `.env` (provide `.env.example`). Never commit keys, never print them.
10. Do not download files larger than about 1 GB without asking. Stream large datasets.
11. Small commits. Run tests before declaring a phase done.

## Data privacy rules
1. Uploaded data is processed locally. Never send raw uploaded data to any external API.
2. LLM policies only ever see compact bucketed synthetic states (age band, occupation class, health group, risk level, active measures), never raw records.
3. Warn the user in the upload step that uploaded population data may be sensitive and should be aggregated.

## Process rules
1. Work phase by phase. Start each phase with an implementation plan and task list, end it with a walkthrough (built, verified with evidence, assumed, deferred) and STOP for review and approval.
2. Read the current official documentation before using any external API. Do not guess request shapes.
3. If the plan changes, update the plan artifact before changing code.

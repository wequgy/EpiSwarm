# EpiSwarm Studio: Workspace Rules (PART A)

## Project identity
EpiSwarm Studio is a configurable framework for outbreak simulation and response planning. A user supplies a region (population, areas, venues, health-system capacity), chooses or defines a disease, defines response measures, and the framework simulates synthetic residents with homes, workplaces, schools or social spaces, health attributes and traits. It compares measures under stated assumptions and recommends which areas to act on first and which measures to take first. It does not predict when the outbreaks happen, but can simulate outbreaks.

## Honesty rules (highest priority)
1. Never invent data, statistics, URLs, citations or parameter values. If unknown, leave `null` or use an obviously labeled placeholder with `status: assumed`, and list it in `ASSUMPTIONS.md`.
2. Every parameter and every data file carries provenance: `source` (URL or citation) and `status` in {`user_supplied`, `sourced`, `assumed`, `synthetic`}. Every run report and every UI page shows the list of `assumed` and `synthetic` inputs in use.
3. Separate what is verified (tests passed, checked against a source) from what is assumed or untested in every summary.
4. Never claim validation that was not run. Without user-supplied observed data, every report says "UNCALIBRATED".
5. The behavior layer (LLM-driven decisions) is not validated for any region unless the user supplies observed data to validate against. Show a persistent "behavior layer unvalidated for this region" banner by default.
6. Synthetic fixture data exists only to build and test code. Any run using synthetic input shows a SYNTHETIC DATA banner and is never described as a result about a real place.
7. Rumor, misinformation and compliance of the public are to be implemented.

## Generality rules
1. No region, country, city or disease constants in `src/`. Everything comes from packs (region, disease, behavior, scenario) and config. Add a test that fails if `src/` contains hardcoded place names or disease names.
2. Area hierarchy is user-defined (for example ward, zone, city), up to three levels, with names chosen by the user.
3. Disease is a user-editable state graph, not hardcoded compartments.
4. Units and labels come from the region pack metadata. No currency or language assumptions in the engine.

## Engineering rules
1. Python 3.11. Agents are structure-of-arrays (one NumPy array per field). No per-agent Python objects, no Mesa.
2. Infection is computed per venue layer with `numpy.bincount` (infectious load per venue divided by venue size), not pairwise contact lists. Use Numba only after profiling.
3. All randomness flows from one seeded `numpy.random.Generator`. Same packs plus config plus seed must reproduce results exactly.
4. All inputs validated with pydantic and a data-contract validator. No magic numbers in code.
5. Every run writes a manifest (git hash, pack hashes, seed, timestamps, list of assumed or synthetic inputs).
6. Target machine: 16 GB RAM, Core i5, RTX GPU. Peak memory under about 11 GB. Per-agent daily history, use this for simulating spread; log aggregates by area, age band and health state plus state-change events, use this to store daily logs.
7. pytest for every module, with invariants: population conserved, no negative counts, absorbing states stay absorbing, same seed reproduces results.
8. Secrets only in `.env` (provide `.env.example`). Never commit keys, never print them.
9. Do not download files larger than about 1 GB without asking. Stream large datasets.
10. Small commits. Run tests before declaring a phase done.

## Data privacy rules
1. Uploaded data is processed locally. Never send raw uploaded data to any external API.
2. LLM policies only ever see compact bucketed synthetic states (age band, occupation class, health group, risk level, active measures), never raw records.
3. Warn the user in the upload step that uploaded population data may be sensitive and should be aggregated.

## Process rules
1. Work phase by phase. Before coding a phase, produce an implementation plan and task list. After finishing, produce a walkthrough (what was built, how verified, what is assumed, what is deferred) and STOP for review.
2. Read the current official documentation before using any external API. Do not guess request shapes.
3. If the plan changes, update the plan artifact before changing code.


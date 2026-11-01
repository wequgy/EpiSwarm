# EpiSwarm Studio: Antigravity prompt pack (framework version)

Two parts. PART A goes in a workspace rule (persistent instructions). PART B is the kickoff prompt you paste into Agent Manager in Planning mode.

Difference from the earlier Bengaluru-only prompt: nothing about any one city, country or disease is hardcoded. Users bring their own population, area, hospital and disease inputs. Bengaluru is just one example region pack (Appendix).

---

# PART A. Workspace rule

Save as `.agents/rules/episwarm.md` in the project workspace (older `.agent/rules/` is also supported). Set it to always apply.

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

---

# PART B. Kickoff prompt

Paste everything below into Agent Manager (Planning mode).

## 1. Mission
Build EpiSwarm Studio: a framework plus a Streamlit app where a user can

1. describe a region (any country) by supplying population and area data, workplaces and schools by area, and hospital and oxygen capacity,
2. choose a disease preset or define their own disease (including replaying a past disease with adjusted parameters),
3. define response measures and objectives,
4. run an agent-based outbreak simulation with a healthcare-overflow model and an optional LLM behavior layer,
5. get a comparison of measures and an advisor recommendation: which areas are hit first, where the health system overflows first, which first measures work best, and who each measure leaves behind.

Claims are always of the form "compared under these assumptions," never "predicted."

## 2. Scope
In scope: person-to-person transmitted diseases that can be expressed as a state graph with age- and risk-dependent transitions (respiratory and contact-type diseases) rumor modeling and compliance of the population. Out of scope for v1: vector-borne and waterborne transmission (dengue, cholera, malaria), which need environment or vector modules. Leave a documented extension interface (`TransmissionModule`) for them and say clearly in the UI and model card that v1 does not cover them.

Non-goals: forecasting,real personal data, reinforcement learning (optional last phase).

## 3. Core abstractions (packs)
Everything the engine needs comes from four packs, each a folder with a YAML file and data files.

### 3.1 RegionPack (`regions/<name>/`)
`region.yaml`: name, country (ISO code, used to pick default contact matrices), data year, area level names (for example [ward, zone]), notes, data level per file.

Three input levels, so users can start with little data:
- **L0 Quick region:** total population, number of areas (or names plus population shares), age pyramid (choose a bundled one or upload), average household size, urban/rural, employment rate, number of schools and markets, total hospital beds by category. Everything else is generated and marked `assumed`.
- **L1 Area table:** per-area population, households, area size, centroids, jobs, schools, markets, hospital beds by category.
- **L2 Full:** adds age by area, venue size distributions, commuting flows between areas, hospital list with locations, time-varying capacity, oxygen supply, observed cases, policy timeline.

Files (CSV in the pack, all optional beyond L0 inputs, every file with `source` and `status` columns where it holds numbers):

| File | Key columns |
|---|---|
| `areas.csv` | area_id, name, level, parent_id, population, households, area_km2, lat, lon |
| `age_structure.csv` | area_id (or ALL), sex, age_band, share |
| `employment.csv` | area_id, jobs, employment_rate (optional by sex and age band), sector_shares |
| `venues.csv` | area_id, venue_type (school/workplace/market/transit/care/other), count, mean_size, size_sd |
| `commute_od.csv` | from_area, to_area, share |
| `contacts.csv` | layer (home/school/work/other), age_band_i, age_band_j, contacts_per_day (or `contact_country: <ISO>` in `region.yaml` to use a bundled default) |
| `hospitals.csv` | hospital_id, name, area_id, lat, lon, sector|
| `capacity.csv` | date (or `static`), hospital_id or area_id, category (general/hdu/icu/icu_vent), nominal, effective_low, effective_high, availability of medicine stock, other parameters, upper_cap_of_extra_resources_that_can_be_allocated(like, additional beds/ medicines etc) |
| `comorbidity.csv` | age_band, sex, condition, prevalence |
| `observed_cases.csv` | date, positives, hospitalized (optional), deaths |
| `policy_timeline.csv` | date_start, date_end, measure, stringency (0 to 1), area_id or ALL |
| `sanitation` | various sanitaion parameters that might affect the disease spread.

Built-in defaults: bundle Prem et al. synthetic contact matrices (home/school/work/other, 16 five-year age bands, many countries, urban and rural variants where available) with provenance, and look for a bundled age pyramid source (for example UN World Population Prospects). Verify license and availability before bundling anything. If a default is not available for a country, require the user to upload it.

### 3.2 DiseasePack (`diseases/<name>.yaml`)
A state graph, not hardcoded compartments:
- `states`: names, flags (`infectious`, `needs_bed: general|hdu|icu|icu_vent|none`, `absorbing`), relative infectiousness per state.
- `transitions`: from, to, probability as a function of age band and risk class (table or function), duration distribution (type and parameters).
- `transmission`: mode `person_to_person`, either `beta` or `R0` (the engine calibrates beta from R0, see 4.3), overdispersion parameter for infectiousness, optional seasonality, optional waning immunity.
- `severity_by_age` table (hospitalization, ICU, case fatality given care), `comorbidity_risk_multipliers`.
- `overflow`: mortality multiplier when a needed bed or oxygen is unavailable (assumed unless sourced).
- `disease_specific_risks`: risks related to diseases and other factors specific to the disease.
- Provenance on every number.

Presets: create `respiratory_generic` and a small number of presets for historical diseases, but ONLY with parameters you can cite from sources you actually found. Anything you cannot cite is `assumed`, and the preset says so. Do not fill numbers from memory. The user can clone a preset, edit any parameter in the UI, or import a YAML.

Sanity checks on any disease pack: probabilities in [0, 1], outgoing transition probabilities sum to 1 per state, durations positive, R0 and overdispersion in plausible ranges (warn, do not block), at least one absorbing state reachable.

### 3.3 BehaviorPack (`behavior/<name>.yaml`)
- Decision questions (id, type Choice/Score/Noul-style yes-no, options, plain-language instructions), for example: workplace attendance (usual/reduced/avoid), market and leisure visits, wear a mask, isolate when symptomatic, accept vaccination when offered.
- Bucket definitions (age band, occupation class, comorbidity flag, trust band, risk-tolerance band, health-state group, local risk level, active measures, household-member-sick flag).
- A free-text `context` field (culture, setting, language, typical constraints) injected into every question's instructions so users can adapt it to their place.
- Trait distributions by archetype (`assumed`, editable).
- Individual agents have varying parameters for: rumor spread and level of compliance to the policies/guidelines.

### 3.4 ScenarioPack (`scenarios/<name>.yaml`)
- Seeding (area, number of index cases, or "seed every area in turn" for the spread matrix).
- Time horizon, scale (number of agents).
- Interventions: alert timing and reach, school/workplace/market closure by area and time window, mask promotion, vaccination priority (if a vaccine is configured), private-bed reservation share, surge beds (count, delay), oxygen buffer. Each with a cost proxy (lost agent-days of work or school plus optional fixed costs).
- Objectives and targets (for example no ICU overflow, deaths below a fraction of baseline).

## 4. Module specifications

### 4.1 Region builder and importer
- Loaders for CSV and XLSX. A column-mapping wizard: the user uploads a file, maps its columns to the schema, and picks units. A validation report lists errors, warnings and provenance per field.
- Downloadable CSV templates with example rows for every file.
- `scripts/validate_region.py` checks names, types, ranges and sums (shares sum to 1, populations non-negative, areas referenced exist) and prints a status table per file: USER_SUPPLIED, DEFAULT, ASSUMED, SYNTHETIC or MISSING.
- L0 builder generates every missing table from the quick inputs using documented formulas and marks them `assumed`.

### 4.2 Population and venues
- Agents allocated to areas in proportion to population, rounded so area totals match within 1%. One agent represents (total population / agent count) people; print this ratio on every report.
- Households composed from household sizes and age structure (at least one adult).
- IPF (iterative proportional fitting) to build joint distributions of age by sex by occupation by area from marginals.
- Venues per area from `venues.csv` or generated from `employment.csv` and school counts; sizes drawn from the size distribution. Workers assigned to a workplace in their own or another area using `commute_od.csv`, or a gravity model (area populations and centroid distances) if flows are missing.
- Fields: id, area ids at each level, household_id, age, sex, occupation_class, workplace_id or school_id, commute_area, wfh_possible, comorbidity flags and `risk_multiplier`, immunity or vaccination status, susceptibility, infectiousness (overdispersed draw), traits (trust, risk tolerance, conscientiousness).

### 4.3 Generic infection engine
- Layers: household, school, workplace, community (area), transit or market. Infection pressure per layer from the contact matrices, scaled by venue size. Closures zero or scale a layer per area and time window.
- Disease state machine driven entirely by the DiseasePack. Durations drawn from the configured distributions.
- `beta` from `R0` using R0 = (beta / gamma) x spectral radius of the contact matrix as a starting guess, then calibrated numerically in the agent model so a single seeded case in a fully susceptible population produces the target R0 on average. Report the calibration.
- Seeding per ScenarioPack.

### 4.4 Healthcare capacity and overflow
- Bed categories as in the capacity file, per area and per hospital where available, with government and private shares if provided.
- Routing: a patient needing a bed goes to the nearest area with free capacity in the right category. if none, the patient is `unserved`. Inflow from outside the region is a configurable fraction of demand.
- Unserved or delayed patients get the disease pack's overflow mortality multiplier, include individuals complaince level multiplier also(compliant individual decreases the chance of mortality, non-compliant person increases the change of mortality).
- Capacity may be time-varying (surge beds, quota changes) and is run as a range (`effective_low` to `effective_high`) in sensitivity analysis.
- Metrics by area: peak occupancy per category, days over capacity, unmet demand, deaths attributable to overflow.

### 4.5 Behavior layer
`DecisionPolicy.decide(situation, buckets) -> probabilities`, with implementations:
1. `RulePolicy`: trait- and symptom-driven probabilities. Always available, used as fallback and as the baseline.
2. `JevPolicy` (TypeSafe AI Jev, a decision model returning typed answers with probabilities): endpoint `https://api.typesafe.ai/v1/systemone`, Python SDK `pip install typesafe-sdk`, key in `TYPESAFE_API_KEY`, model `jev-latest`. Question types are Choice, Score and Noul (yes/no style). Question IDs are not sent to the model, so put all requirements in each question's instructions. It returns probabilities and no reasoning. Read the current docs first and test access before relying on it.
3. `GeminiPolicy` (optional, for ensemble checks and showcase-agent explanations) using the `google-genai` SDK, model name from `GEMINI_MODEL`, with rate-limit backoff.
4. Optional `OpenAICompatiblePolicy` for any OpenAI-compatible endpoint set in `.env`, so users can plug their own model.

Design rules:
- Input is a compact bucketed state, never free-text persona or raw records. Keep buckets coarse (hundreds, not thousands).
- Call the policy only when a trigger fires (new measure, risk-band change, symptom onset, sick household member). Cache every answer on disk by (bucket, situation) in SQLite. Use async calls with a concurrency limit and batch several questions per request where allowed.
- **Sample each agent's action from the returned probabilities; never take the argmax.** Add trait-based noise. LLM agents tend to be too uniform and over-compliant, so add a variance check report and an ablation (Rule vs LLM policies on identical situations).
- For hypothetical-disease runs, never name a real pathogen in a prompt.
- If an API fails, fall back to `RulePolicy` and log the fallback rate.

### 4.6 Analysis
- **Spread matrix:** seed in each area in turn over many seeds; report mean days until first case in every other area and the order areas are hit.
- **Equity:** outcomes by area, age band and density quintile; gap between worst-off and best-off groups.
- **Objective vector:** deaths, peak ICU occupancy and days over capacity, unmet demand, cost proxy, equity gap.
- Report 30 or more seeds by default with confidence intervals.

### 4.7 Advisor and optimizer
- Advisor uses LLM function calling (Gemini by default, provider-pluggable) with tools `run_scenario(config)`, `get_metrics(run_id, by)`, `compare(run_ids)`, `list_measures()`, plus a JSON memory of past runs. Loop: baseline, read which areas are hit first and where capacity overflows, pick the next measure, run, compare. Stop when the objective target is met or the run budget is used. Output a pydantic `Recommendation` (areas to act on first, first three measures in order, evidence with run ids, caveats).
- `optimize/search.py`: multi-objective search (Optuna, NSGA-II) over measure mix and timing, producing a Pareto front.
- Compare three arms: advisor alone, search alone, both. On a tiny action space also brute-force the true best policy and report how close each arm gets.
- Failure handling: validate and retry a malformed tool call once, fall back to the deterministic search, flag fallbacks in the log, and always present the result as a recommendation for human decision-makers.

### 4.8 Calibration and validation (optional, only if the user supplied observed data)
- Fit seeding, beta and compliance to `observed_cases.csv` with `policy_timeline.csv`, scale infections to reported cases with an ascertainment factor, report fit quality honestly including failures. Hold out a later period if there is one.
- Without observed data this module is disabled, and every report is labeled UNCALIBRATED.
- Sensitivity analysis (one-at-a-time and, if time allows, Sobol) over R0, ascertainment, compliance, capacity range, overflow multiplier and contact assumptions; state which recommendations change.

## 5. Studio app (Streamlit + Plotly)
Guided steps, with a persistent status panel showing provenance (USER_SUPPLIED / DEFAULT / ASSUMED / SYNTHETIC) and banners for synthetic data and "behavior layer unvalidated":
1. **Region:** pick an example pack, upload files with the column mapper, use the Quick Region builder, or edit tables in place.
2. **Disease:** pick a preset, clone and edit every parameter, edit the state graph, or import YAML.
3. **Health system:** enter beds, ICU, oxygen per area (a "beds per 1,000" shortcut), static or time-varying.
4. **Measures and objectives:** build a scenario.
5. **Run:** choose scale, seeds, behavior policy.
6. **Results:** spread map or grid, capacity occupancy, scenario comparison with intervals, Pareto front, equity, spread matrix.
7. **Advisor:** run the advisor and show its steps, tool calls and recommendation.
Also export a PDF or HTML report with the inputs, assumptions list, results and limitations.

## 6. Scale and performance (measure and report, do not assume)
Debug 5,000 agents, default 50,000, stretch 100,000 and above. `scripts/benchmark.py` reports time and memory at 5k, 50k, 100k and 500k agents. Parallelize across seeds with multiprocessing.

## 7. Repository layout
```
episwarm/
  README.md  ASSUMPTIONS.md  DATA_SOURCES.md  MODEL_CARD.md
  pyproject.toml  .env.example  .gitignore
  regions/      example_bengaluru/  example_synthetic/
  diseases/     respiratory_generic.yaml ...
  behavior/     default.yaml
  scenarios/    baseline.yaml ...
  src/episwarm/
    packs/       region.py disease.py behavior.py scenario.py schema.py
    importers/   csv_xlsx.py mapper.py templates.py validate.py quick_region.py
    population/  build.py households.py venues.py traits.py
    engine/      state_graph.py contacts.py infection.py healthcare.py interventions.py sim.py
    behavior/    buckets.py policy_base.py policy_rules.py policy_jev.py policy_gemini.py policy_openai_compat.py cache.py
    advisor/     tools.py agent.py schemas.py memory.py
    optimize/    objectives.py search.py surrogate.py
    analysis/    metrics.py equity.py calibration.py sensitivity.py spread_matrix.py variance_check.py
    app/         streamlit pages
  scripts/       benchmark.py validate_region.py make_synthetic_region.py check_apis.py
  tests/
```

## 8. Phases (stop for review after each)
- **Phase 0:** scaffold, pydantic schemas for all four packs, templates, validators, synthetic example region, `check_apis.py` (one tiny call to each configured API, prints OK or FAIL, never prints keys), `DATA_SOURCES.md`. Acceptance: validators pass on the synthetic region and reject deliberately broken inputs with clear messages.
- **Phase 1:** region importer, Quick Region (L0) builder, population and venue builder. Acceptance: area totals within 1% at 5k, 50k and 100k agents; reproducible; population summary report; works from L0, L1 and L2 inputs.
- **Phase 2:** generic disease state-graph engine and infection layers, benchmark script. Acceptance: conservation tests; R0 calibration report; the same engine runs two different disease packs without code changes.
- **Phase 3:** healthcare capacity, overflow and oxygen. Acceptance: overflow tests with known demand against known capacity.
- **Phase 4:** behavior layer with Rule, Jev and caching; variance check; ablation harness. Acceptance: runs with API access and with fallback only.
- **Phase 5:** interventions, spread matrix, equity analysis.
- **Phase 6:** advisor and optimizer with the three-arm comparison.
- **Phase 7:** Studio app including the column mapper.
- **Phase 8:** optional calibration module (needs observed data), sensitivity analysis, `MODEL_CARD.md` (intended use, limits, what is assumed, behavior-layer caveat, diseases not covered).
- **Phase 9:** optional surrogate model plus reinforcement learning, verified on the full agent model. Only if asked.

## 9. First task
Do Phase 0 only. Write the implementation plan and task list for Phases 0 and 1, show the proposed pydantic schemas for the four packs and the file templates, then wait for my approval before writing code.

---

# APPENDIX. Example region pack: Bengaluru (build in Phase 1 after the framework works)

Real inputs the user may supply; the agent must verify each source and document it, never guess:
1. **Ward census 2011** and **BBMP ward public goods** (OpenCity): ward population, SC/ST, male/female, zone name, area, households, government schools. Group wards into zones using the zone column.
2. **Ward boundaries** (OpenCity BBMP Ward Information: 2015 map with 198 wards, 2022 map with 243 wards, 2022 zone boundaries). Check that ward numbering matches the census file; if not, join by name or work at zone level.
3. **Daily Bengaluru COVID-19 data, June 2020 to Feb 2023** (OpenCity): positives, discharges, deaths.
4. **Policy timeline**: Oxford COVID-19 Government Response Tracker (India) plus Karnataka lockdown dates.
5. **Contact matrices**: Prem et al. synthetic matrices for India (urban).
6. **Severity**: Levin et al. 2020 age-specific infection fatality anchors (about 0.4% at age 55, 1.3% at 65, 4.5% at 75, 15% at 85; Eur J Epidemiol 35:1123-1138) with log-linear interpolation; hospital and ICU fractions from cited sources.
7. **Personas**: Nemotron-Personas-India (Hugging Face, CC BY 4.0, adults only, no health fields); stream and filter, use for showcase agents only.
8. **Hospitals and capacity**: effective vs nominal beds by category and zone from primary sources where possible (news-only sources marked). Official 2020 figures were disputed, so record ranges and calibration anchor dates (for example reported ICU saturation around September 2020 and April 2021, and oxygen allocation changes in April to May 2021).
9. **Age and sex by ward**, **commuting flows**, **oxygen supply**, **serosurveys**, **comorbidity prevalence** (NFHS-5, ICMR-INDIAB): find if possible, otherwise use L0 or L1 fallbacks marked `assumed`.
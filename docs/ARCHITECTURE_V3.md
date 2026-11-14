# EpiSwarm Architecture v3

Save in the repo as `docs/ARCHITECTURE_V3.md`. It supersedes the earlier spec where they conflict (section 13 lists what it replaces). `docs/IMPLEMENTATION_SPEC.md` remains the reference for equations (Libin et al. metapopulation engine, R0 calibration, unserved-outcome model).

## 0. Constraints this design must honor
- **C1. Agentic and LLM-central.** LLMs are core to the product and must be used where they add the most value, not decoratively.
- **C2. Any region, any disease.** Nothing about a place or pathogen lives in code. Everything arrives through packs, so the framework can be scaled up later.
- **C3. Realism comes from evidence.** The engine is universal; realism scales with the evidence supplied, and the product says how much evidence a result rests on.
- **C4. Integrity.** No fabricated data, no hand-typed results, no unverified claims. This is enforced by code, not by instructions.
- **C5. Scale-up.** Designed to grow to millions of agents, many regions and many users without redesign.

## 1. Core idea
**A universal engine, plugged into evidence, with LLMs as the intelligence around it.** The simulation core is deterministic and fast (arrays, seeded). LLMs do the work humans would otherwise do slowly or not at all: assembling evidence for a new region or disease, hypothesizing and teaching behavior, authoring scenarios, planning and explaining decisions, and critiquing the model. They are never allowed to invent a number that enters the engine without a ledger entry.

## 2. Layers
| Layer | Contents |
|---|---|
| L0 Evidence | Region, disease, behavior and scenario packs; the **Evidence Ledger**; onboarding agent; hierarchical priors |
| L1 Population and contacts | Hybrid contact structure: explicit persistent links for households, schools and workplaces plus mean-field community mixing; calendars; life histories |
| L2 Disease | State graph with roles; vulnerability factors; environment modifiers; immunity, vaccination and variant modules |
| L3 Health system | Resource-generic patient pathways, occupancy and non-outbreak demand, individual-factor outcomes for unserved patients |
| L4 Behavior | Three-tier behavior model (data-constrained, distilled LLM-teacher student, live LLM for out-of-range cases and showcase agents); compliance, fatigue, norms; rumor |
| L5 Observation and inference | Observation model; calibration (screening on the meta engine, then SMC-ABC or Bayesian optimization on the agent engine); posterior ensembles; validation |
| L6 Agents | Onboarding, Scenario Author, Advisor, Critic, Narrator |
| L7 Platform | FastAPI service, job queue, React/TypeScript web app, diorama |

## 3. LLM roles (where they earn their place)
| Role | What it does | Guardrails | How its value is measured |
|---|---|---|---|
| **Onboarding agent** | Given a region or disease name or user files, finds sources, maps data to the contract, proposes parameter priors with citations, flags gaps | Cannot write a number without a ledger entry; second independent verification pass; influence-ranked human review queue; stops and asks if data are unavailable | Pack accuracy and time versus a hand-built pack for the reference site |
| **Behavior teacher** | Labels how different kinds of people respond in many situations (probability vectors); ensemble of models and paraphrases | Outputs are priors, not truth; calibrated against data when available; bias reported | Distribution match to contact-survey data after calibration; ablation against rule and data-only versions |
| **Scenario author** | Natural language to validated ScenarioPack | Schema validation; shows the parsed result for confirmation | Parse accuracy on a test set |
| **Advisor** | Tool-calling loop over run, compare and metrics, on posterior ensembles, with a deterministic search as co-pilot | Request budget; schema validation; no claim without run ids; fallback to search | Regret versus brute-force on small action spaces |
| **Critic** | Reads training-window diagnostics, proposes ranked hypotheses for model error and the experiments to test them | **Blind to held-out results**; proposals need human approval | Fraction of accepted proposals that improve training-window skill |
| **Narrator** | Explanations, showcase-agent narratives, reports | Labeled GENERATED NARRATIVE; never feeds the engine | Human review |

## 4. Evidence layer
**Evidence Ledger** (SQLite plus Parquet export). One row per parameter or data file:
`param_id, pack, value_distribution (type and parameters), unit, source_url, source_type (dataset|paper|official|news|llm_estimate), locator (page, table or figure; excerpt of at most 15 words), retrieved_at, sha256 (for files), extraction (script|human|llm), verified_by (human|second_llm|none), evidence_class, influence_score, review_state`.
Evidence classes: **A** measured in this region, **B** measured elsewhere and transferred, **C** LLM or expert prior. Class C values carry wide distributions.

**Hierarchical priors:** parameters inherit from global to country to local levels (for example contact matrices by country, age-specific severity from meta-analyses, behavior response curves from other regions), then local data update them. This is how any region works with little data without pretending to certainty.

**Onboarding agent flow:** resolve region and disease; propose a source plan; fetch and checksum files (or stop and list exact manual downloads); map to the contract; propose priors with citations; verify; rank parameters by influence (from sensitivity analysis); queue the top ones for human review; emit a pack plus a **trust report**.

## 5. Contact structure (hybrid network)
- **Explicit links** for household, school-group and workplace-team layers: edge arrays (src, dst, layer, weight), partners sampled using the age-structured contact matrices, with a per-day activation probability (published agent models activate a random subset of fixed connections each day; for example OpenABM-Covid19 uses a random half of fixed connections plus a daily random network).
- **Mean-field community layer** per area (existing `bincount` approach) with commuting flows for cross-area exposure.
- **Transmission** along active edges: `p = 1 - exp(-beta_layer * infectiousness_i * susceptibility_j * (1 - protection))`, computed vectorized over active edges only; closures and isolation deactivate layers per area or agent.
- **Time structure:** day-of-week, term and holiday calendars as pack inputs; time-varying contact multipliers by age and setting from data when available.
- **Memory:** 1M agents with about 15 links each is about 15M edges, a few hundred MB as typed arrays.
- **Calibration:** beta per layer relative weights from the ledger, overall scale from an expectation-based R0 calculation on the actual network, verified by Monte Carlo with at least 2,000 index trials and common random numbers.

## 6. Behavior system (LLMs used well)
**Principle: spend LLM calls on teaching and exceptions, not on every agent every day.** Per-agent, per-day LLM calls are costly, nondeterministic and cannot be calibrated. A distilled student gives every agent a distinct, reproducible, calibratable decision at array speed.
- **Tier 1, data constraints.** When contact or mobility data exist, per age, setting and period multipliers constrain aggregate contact rates; individual heterogeneity stays.
- **Tier 2, distilled student (default).** Features per agent and day: traits, life history, risk perception, norm, fatigue, rumor belief, active measures. A parametric student (logit or small boosted trees) is fit to **teacher** labels from an ensemble (two or three models, several paraphrases, shuffled option order) on a space-filling design of feature settings. It is then calibrated to data (temperature and offsets) when available, otherwise flagged uncalibrated with widened uncertainty (bootstrap or Bayesian coefficients). Coefficients come from fitting, never typed in.
- **Tier 3, live LLM.** Used for showcase agents (explanations), for out-of-range situations (distance to the teacher design above a threshold, which triggers new teacher queries, caching and an offline retrain between runs, never mid-run), and for scenario authoring.
- **Ensembling and bias control:** teacher ensembles, option-order averaging, prompt-sensitivity reports, variance checks. Published work found LLM agents match average compliance but are too uniform and over-compliant, and that ensembling helps; the calibration layer is what fixes this.
- **Rumor and compliance:** social graph, belief dynamics, correction campaigns, fatigue and norms as in the spec, with effect sizes from the ledger.
- **Ablation always available:** none, rule, student(uncalibrated), student(calibrated), data-only.

## 7. Disease and health system
Disease state graph with roles (susceptible, exposed, infectious, symptomatic, needs-care, recovered, dead) instead of names; age and risk dependent transitions; disease-specific vulnerability factors; environment modifiers; optional modules for immunity waning, vaccination and variants. Health system: generic resources, hospital-level capacity time series, non-outbreak occupancy, length-of-stay by age, unserved-outcome model depending on self-care, support, alternative access, delay and severity.

## 8. Observation and inference
- **Observation model:** onset, test, report and admission delays, time-varying ascertainment, day-of-week effects, death delays, occupancy by category.
- **Pipeline:** priors from the ledger, then screening on the meta engine (fast), then calibration on the agent engine (SMC-ABC such as `pyabc`, or Bayesian optimization with a likelihood on the observation model), then a posterior ensemble (about 200 draws), then scenario runs across the ensemble with paired seeds, then results with intervals.
- **Twin experiments** prove the machinery can recover known parameters before touching real data; non-identifiable parameters are reported.

## 9. Integrity architecture (enforced by code)
1. **Provenance gate.** `status: real` can only be written by the downloader, which records URL, retrieval time, size and SHA-256 in the ledger. Loaders refuse `real` data without a matching record. CI fails otherwise.
2. **No synthesized data in validation or calibration paths.** Static checks fail the build if builder or validation modules import random generators or contain numeric literals for observed or simulated results. Synthetic fixtures live only under a `synthetic/` path and always carry a banner.
3. **Validation harness with controls.** Positive control: validating a model against its own data must pass. Negative control: validating against shuffled or deliberately wrong data must fail. Both run in CI.
4. **Single source of truth.** Reports are rendered from the machine-readable validation card only; the status string is computed from metric versus threshold in code, never typed. Tests assert that no "PASS" appears for a failing metric.
5. **Held-out lock.** Held-out data are read only through a gate that requires a committed protocol hash and appends to an append-only log; calibration, critic and tuning code cannot import it (import-linter rule). Re-evaluation after changing parameters creates a new model version and is flagged.
6. **Human spot-check.** For each real dataset the user verifies five values against the source (checklist generated by the tool).
7. **Stop, don't substitute.** If real data cannot be obtained, the agent marks MISSING and stops; it never generates a stand-in.

## 10. Validation and trust tiers
- **Explorer:** assumption-based results; any class C evidence allowed. **Calibrated:** fitted to the user's local data with an observation model. **Validated:** passed pre-registered held-out tests for the stated targets.
- Every result page shows its tier, the failed targets, and the assumptions.
- **Reference site** (England, London or a region): proves the method end to end, with curves, spatial order, overflow and behavior validated against real data.
- **Transportability study:** run the onboarding pipeline on two more sites with different data richness and report accuracy against data richness. This is how "any region" is earned.

## 11. Platform
- **Backend:** FastAPI with versioned routes under `/api/v1`, Pydantic v2 models, OpenAPI schema, typed TypeScript client generation (`openapi-typescript` or `orval`), a persistent job table (SQLite, later Postgres) with a process pool, server-sent events for progress, runs stored as Parquet or NPZ with manifests.
- **Frontend:** React, TypeScript, Vite, TanStack Query, a small state store, Tailwind with a component library, ECharts or Plotly for curves, the Anatomy-built diorama as an embedded module. Tests: Vitest and Playwright.
- **Packaging:** Docker Compose for api and web, lockfiles, CI for backend and frontend, environment-based configuration, no secrets in the repo.
- **Streamlit** is deprecated and removed after parity.

## 12. Scale-up
Array-based engine with area-partitioned work, deterministic RNG streams per area, Numba for hot loops, GPU only where profiling shows a gain, job queue that can move to a worker pool, run manifests for reproducibility, pack versioning, and multi-region support through the pack registry.

## 13. Supersedes
Spec 4.1 (venue-only mean-field mixing) by section 5; spec 10 (per-bucket LLM policy calls) by section 6; any hand-typed behavior coefficients; Streamlit as the primary UI by section 11; prior validation artifacts in `regions/london/` and `docs/validation/` which are quarantined until rebuilt from real data.

## 14. Risks
Teacher bias propagates to the student (calibration and ensembles mitigate, tiers disclose); hierarchical priors may transfer poorly across cultures; onboarding agents can mis-extract numbers (second pass and influence-ranked review); explicit networks add memory and calibration work; real data are biased and revised; one reference site does not prove generality (hence the transportability study).

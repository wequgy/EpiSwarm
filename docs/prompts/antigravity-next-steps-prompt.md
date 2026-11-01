# EpiSwarm Studio: next-steps prompt (Phases 9 to 14)

How to use: (1) copy `episwarm-implementation-spec.md` into the repo as `docs/IMPLEMENTATION_SPEC.md`. (2) Paste everything below into Agent Manager in Planning mode. The workspace rule file stays as it is; this prompt tells the agent to update it.

---

## 0. Context
You reported that Phases 0 to 8 of EpiSwarm Studio are complete. The user is a student, not an expert, and says they do not understand what was built. You also never asked about API keys, so the LLM paths (Jev, Gemini) have probably only been exercised through the rule-based fallback. Treat your own earlier "passed" claims as unverified until you show evidence.

The user's requirements are in the edited framework prompt (`antigravity-episwarm-framework-prompt-altered.md`, if it is in the repo, otherwise in the plan artifacts) plus the additions in section 3 below. The technical reference is `docs/IMPLEMENTATION_SPEC.md`; read it fully before planning. Follow the existing workspace rules (honesty, structure-of-arrays, seeded randomness, provenance on every parameter, phase-by-phase with a stop after each).

Platform: Windows with PowerShell, Python 3.11, 16 GB RAM, Core i5, RTX GPU, peak memory budget about 11 GB. Use `pathlib`, avoid bash-only commands, and keep multiprocessing Windows-safe (`if __name__ == "__main__":`, picklable top-level functions).

## 1. Ground rules for this round
1. Evidence, not claims. For every statement of the form "X works", run a command and show its real output (pytest summary line, benchmark table, screenshot or `AppTest` result).
2. Do not ask the user to paste API keys into chat, ever. Keys are entered locally through a script (section Phase 9). Never print or log a key.
3. Never invent data, citations, URLs or parameter values. Unknown means `null` or a labeled placeholder with `status: assumed`, listed in `ASSUMPTIONS.md`.
4. Work phase by phase. Start each phase with an implementation plan and task list, end it with a walkthrough (built, verified with evidence, assumed, deferred) and STOP for approval.
5. Update `.agents/rules/episwarm.md` once, at the start of Phase 9, so it reflects: rumor, misinformation and compliance are in scope; no resource-specific names (including oxygen) in `src/`; never ask for keys in chat; Windows constraints; per-agent daily history allowed for simulation, with only aggregates written to disk; evidence-before-claims.

## 2. Phase 9: audit, plain-language explanation, API setup (no new model features; the local decision backend in 9D is the one exception)
**9A. Audit.** Produce `docs/STATUS.md`: a table with one row per requirement from the framework prompt, the user's edits and section 3 below. Columns: requirement, status (IMPLEMENTED / PARTIAL / MISSING / STUBBED), file and function, test that covers it, evidence (command run and result). Be blunt. In particular, state whether each of these exists today: rumor and misinformation layer, compliance model, sanitation/environment inputs, disease-specific risk factors, individual-factor outcomes for unserved patients (not a single multiplier), per-agent life histories, resource what-if, social-space venues.
Run and show the output of: `pytest -v` (report the number of test files, test functions and the final summary line; clarify what "40 suites" meant), `python scripts/benchmark.py`, and a headless run of every Studio step with `streamlit.testing.v1.AppTest`. Check the benchmark numbers for plausibility (memory at 100k agents, time per run) and explain how they were measured.
Find tests that are weak or tautological (for example "variance > 0") and strengthen them. Do the mutation sanity check from the spec (break five key behaviors on purpose, confirm tests fail, revert).

**9B. Plain-language documents** for a non-expert:
- `docs/WHAT_WAS_BUILT.md`: what the system does in simple words; a map of the repository (folder by folder, one sentence each); what is real, what is placeholder, what is synthetic; what has NOT been tested with real data or live APIs.
- `docs/ARCHITECTURE.md`: a Mermaid data-flow diagram showing input, agent, decision and action, with every tool call, memory read or write, and external API call marked (Jev, Gemini, SQLite cache, files). Keep it readable, about 10 to 12 nodes.
- `docs/USER_GUIDE.md`: step-by-step with the Studio, with a glossary (R0, attack rate, overflow, compliance, spread matrix, Pareto front, and so on).
- `scripts/demo.py`: runs the synthetic region end to end and prints a plain-English summary of what happened and which inputs were assumed or synthetic.

**9C. API keys, safely.**
- Create or fix `.env.example` with: `GEMINI_API_KEY` and `GEMINI_MODEL` (needed), `TYPESAFE_API_KEY` (optional and paid, may stay empty), `LOCAL_LLM_BASE_URL` and `LOCAL_LLM_MODEL` (free local backend), and the optional OpenAI-compatible variables.
- Create `scripts/setup_keys.py`: prompts in the terminal with hidden input (`getpass`), writes `.env`, never echoes keys. Confirm `.env` is in `.gitignore`.
- Fix `scripts/check_apis.py` so it prints a status table (service, reachable, latency, rate-limit headers if any) and never prints keys.
- Read the current official docs for Jev (docs.typesafe.ai) and Gemini (`google-genai`) before touching the clients; correct any client code that does not match them.
- Write the exact steps for the user (Windows PowerShell) at the top of `docs/USER_GUIDE.md`: where to get each key, how to run `python scripts/setup_keys.py`, how to run `python scripts/check_apis.py`.
- Do NOT run live LLM tests until the user confirms keys are set. When they are, run a small live test of each policy, record real latency and any rate limits in `DATA_SOURCES.md`, and report the fallback rate.

**9D. Free local decision backend.** Jev is paid (about $0.042 per million input tokens, with no confirmed free tier), so the project must not depend on it.
- Implement `LocalLogprobPolicy(DecisionPolicy)` exactly as in `docs/IMPLEMENTATION_SPEC.md` section 10.2b: single-token option labels, one output token, thinking off, probabilities from `top_logprobs`, normalized over the labels, averaged over shuffled option orders. Support Ollama (verify the installed version returns logprobs), any OpenAI-compatible local server, and an in-process Hugging Face `transformers` fallback that reads next-token logits on the RTX GPU (check available GPU memory and pick a model size that fits).
- Backend selection from config, in this order: Jev if a key is present and healthy, else Local if reachable, else Rule. Log which backend served every call and the fallback rate.
- Extend `scripts/check_apis.py` to test the local engine: reachable, model present, logprobs returned, and one probability vector printed.
- Acceptance: probabilities sum to 1 for every question; a test shows that shuffling option order changes the averaged probabilities by less than a stated tolerance (report the actual numbers); the policy runs fully offline; answers are cached by bucket; the variance check and a Rule-versus-Local ablation run; the 100k-agent benchmark with the local policy reports number of model calls, cache hit rate and total time.
- Do not call the local probabilities calibrated. Run the 5-paraphrase prompt-sensitivity test and report the spread.

Stop after Phase 9 for the user's review.

## 3. Additional requirements (apply in Phases 10 to 13)
Read `docs/IMPLEMENTATION_SPEC.md` for the formulas, data structures and algorithms behind each item.

1. **Simulate and plan modes.** The Studio and the CLI support (a) Simulate: free exploration (run, vary any parameter, sweep, inspect agents) with no advisor, and (b) Plan: scenario comparison and advisor recommendation. Neither mode claims to predict when outbreaks will happen.
2. **Rumor, misinformation and compliance layer** (spec sections 7 and 8): social network, rumor topics, belief dynamics, sharing, correction campaigns, compliance with fatigue and norms, effects on masking, vaccination, isolation and attendance. BehaviorPack gets parameters for all of it. Metrics and counterfactual runs (with and without rumor).
3. **Unique agent life histories** (spec section 9): structured per-agent history and routine, persistent preferred venues, social spaces as venues, generated biographies for showcase agents only (labeled GENERATED NARRATIVE).
4. **Disease-specific vulnerability factors** (spec 5.1): the DiseasePack declares which factors matter and their effects; the RegionPack supplies prevalence (`risk_factors.csv`, generalizing the comorbidity file); population builder assigns factor bits. Show that the same engine behaves differently for two disease packs with different factors.
5. **Environment and sanitation inputs** (spec 5.2) in the RegionPack, used through the disease pack's `environment_modifiers`.
6. **Generic resources** (spec 6.1): remove every resource-specific name (including oxygen) from `src/` and from the data contract; resources are declared in packs and states declare what they need. Add a test that fails if `src/` contains oxygen or any other hardcoded resource name.
7. **Outcomes for unserved or partially served patients** (spec 6.3): replace the single overflow multiplier with the individual-factor model (self-care, support, alternative care access, delay, severity). `theta_0 = 0` must be valid. Compliance is one input to self-care, not the only one.
8. **Additional resources and aids what-if** (spec 6.4): `resource_adds` in ScenarioPack with caps from `upper_cap_of_extra`, paired-seed delta reports, marginal-value sweeps and allocation, and an "Add resources" Studio panel.
9. **Implementation depth from Libin et al. 2020** (spec section 11, 12, 13): the metapopulation engine, cross-validation against the agent engine, Leiden communities, exhaustive-search ground truth, and the optional PPO setup.

## 4. Phase 10: core model changes
Items 4, 5, 6, 7 and 3 (life histories, routines, social spaces, venues). Update schemas, templates, validators, synthetic fixtures, tests and docs. Acceptance:
- The same engine runs two disease packs with different vulnerability factors and environment modifiers and produces different, explainable outcomes.
- Grep test passes: no resource-specific or place or disease names in `src/`.
- Unserved-patient outcomes depend on individual factors; a test shows that with `theta_0 = 0` unserved equals served, and with large `theta_care` low self-care agents do worse than high self-care agents under identical overflow.
- Life-history fields are generated, reproducible by seed, and shown in the Residents view.

## 5. Phase 11: rumor, misinformation and compliance
Item 2. Acceptance (all as statistical tests with paired seeds, not single runs):
- No seeds means no spread; beliefs stay in [0, 1].
- More correction reach lowers mean belief.
- Higher belief lowers compliance and mask use as configured.
- The counterfactual (rumor off) report works and shows deaths attributable to the rumor, with confidence intervals.
- Policy calls still only see bucketed state; belief appears only as a band.
- Add a Studio panel for rumor and compliance settings and a results view.

## 6. Phase 12: resource what-if, modes and Studio updates
Items 1 and 8. Acceptance: baseline versus +X units shows deltas with confidence intervals; adding resources never increases unmet demand in paired seeds; the marginal-value curve and best-area ranking are produced; Simulate and Plan modes both work in the Studio; `AppTest` covers every step.

## 7. Phase 13: Libin-based engine, cross-validation and search
Item 9. Acceptance:
- `engine_meta` implemented per spec section 11, with the binomial-chain or SDE choice documented.
- Cross-validation test between the agent engine and the meta engine with the actual differences reported (peak day, peak height, attack rate); no tuning of tolerances to pass.
- `mu` fitted per region and disease, with the fit shown; no reuse of the paper's constants.
- Leiden (or the documented fallback) communities for the commuting graph.
- Exhaustive ground truth on a small binary policy space; the optimizer arms are compared against it.
- Optional PPO only if the user asks; if not, leave it as a documented extension.

## 8. Phase 14: hardening
- Benchmarks on CPU for 5k, 50k, 100k, 500k agents (time and memory), plus GPU feasibility notes only if profiling shows a benefit.
- Sensitivity analysis including rumor, compliance, resource and `theta` parameters; update `MODEL_CARD.md` (intended use, limits, what is assumed, behavior layer unvalidated unless observed data is supplied, diseases not covered).
- Live-API test report once keys are set: latency, rate limits, fallback rate, ablation of Rule versus Local versus Jev (only if a key exists) versus Gemini on identical situations, variance check.
- Final `docs/STATUS.md` refresh and a short "known limitations" list.

## 9. What to send back at every stop
1. What you built, in plain English (five lines).
2. Evidence: the exact commands you ran and their outputs.
3. What is still assumed, synthetic or untested.
4. Anything you could not do and why.
5. The next phase's plan, then wait for approval.

## 10. First task
Do Phase 9 only. Start with the plan and task list, then run the audit and produce the three documents and the key-setup scripts. Do not start Phase 10.

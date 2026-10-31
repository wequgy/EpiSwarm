# EpiSwarm Studio: Implementation Spec

Save this file in the repository as `docs/IMPLEMENTATION_SPEC.md`. It is the technical reference for the next-steps prompt. Where it gives numbers taken from papers, they are starting points to verify, not truths. Anything not sourced stays `assumed`.

Platform: Windows (PowerShell), Python 3.11, 16 GB RAM, Core i5, RTX GPU, peak memory budget about 11 GB. Use `pathlib`, no bash-only commands, and on Windows put multiprocessing entry points under `if __name__ == "__main__":` with picklable top-level functions (spawn start method).

---

## 1. Stack

| Need | Library | Notes |
|---|---|---|
| Arrays, math | numpy, scipy (incl. `scipy.sparse`), pandas | core |
| JIT (only after profiling) | numba | CPU first; GPU (CuPy or PyTorch) only if profiling shows a benefit at 500k+ agents |
| Validation / config | pydantic v2, pyyaml, python-dotenv | |
| Import | openpyxl (xlsx), pyarrow | |
| Network analysis | networkx (analysis only), igraph + leidenalg (Leiden communities; if Windows wheels fail, fall back to networkx `louvain_communities` and say so) | |
| LLM decisions | Local free backend first: Ollama or any OpenAI-compatible local server (`httpx` + `asyncio`), optional in-process `transformers` + `torch` on the RTX GPU; optional paid `typesafe-sdk` (Jev); `google-genai` (Gemini, advisor and narratives) | Jev is optional |
| Caching | `sqlite3` (stdlib) | |
| Optimization | optuna (NSGA-II) | |
| RL (optional, last phase) | stable-baselines3 + torch | small MLP, CPU is fine; RTX GPU optional |
| App | streamlit, plotly | tests via `streamlit.testing.v1.AppTest` |
| Tests | pytest, hypothesis (optional) | |
| Personas (optional) | `datasets` (Hugging Face, streaming mode) | |

Pin versions at implementation time (lockfile) and record them in `pyproject.toml`.

---

## 2. Agent data structures (structure-of-arrays)
One NumPy array per field, all length N. Suggested dtypes; adjust to need.

| Group | Fields |
|---|---|
| Identity | `id` int32, `area_l1`, `area_l2`, `area_l3` int16/int32, `household_id` int32 |
| Demographics | `age` uint8, `age_band` uint8, `sex` uint8, `occupation_class` uint8, `education` uint8, `income_band` uint8 |
| Venues | `workplace_id`, `school_id` int32 (-1 if none), `routine_template` uint8, `pref_market_id`, `pref_leisure_id` int32 |
| Biology | `risk_factor_bits` uint32 (disease-specific vulnerability flags), `risk_multiplier` float32, `susceptibility` float32, `infectiousness` float32 (overdispersed draw), `immunity` float32, `vaccinated` uint8, `vaccine_day` int16, `prior_infections` uint8 |
| Disease state | `state` uint8, `days_in_state` int16, `state_duration` int16 (drawn at entry) |
| Traits | `trust_authority`, `risk_tolerance`, `conscientiousness`, `self_care`, `support`, `alt_care_access` float32 in [0, 1] |
| Behavior | `compliance` float32, `masking` uint8, `isolating` uint8, `outing_level` uint8, `fear` float32 |
| Rumor | `belief[K]` float32 (K topics), `share_propensity` float32, `gullibility` float32 |
| Life history | `past_bereavement` uint8, `caregiver` uint8, `financial_buffer` float32, `chronic_bits` uint32, `prior_authority_experience` float32 |

Per-agent daily history is allowed on this machine for the agents' own use in simulation (for example last-14-days exposure counts), but logs written to disk are aggregates by area, age band and state plus state-change events. Showcase agents (20 to 50) additionally keep a full event log.

---

## 3. Daily tick (agent engine)

```
for day in range(T):
    1. public_info(day)            # reported cases, active measures, alerts, correction campaigns
    2. rumor_step(day)             # section 7
    3. behavior_step(day)          # triggered policy calls, compliance update (section 8)
    4. attendance(day)             # who is at which venue per layer, given measures and behavior
    5. infection_step(day)         # section 4
    6. progression_step(day)       # state graph transitions
    7. resource_step(day)          # allocation and overflow (section 6)
    8. metrics(day)                # aggregates only
```
Same seeded `Generator` throughout. Use common random numbers (same seed streams) when comparing scenarios, so differences come from the intervention and not from noise.

---

## 4. Infection engine

### 4.1 Contact structure
Prem et al. matrices `M^l[a, b]` give mean contacts per day an individual in age band `a` has with band `b`, for layers `l` in {home, school, work, other}. Treat the `other` layer as community and transit/market.

Within a venue `v` of layer `l`, for an attending agent `i` in band `a`:
- expected contacts per day: `c_l(a) = sum_b M^l[a, b]` (the row sum)
- contacts are distributed over the bands present in the venue with weights `w_b ∝ M^l[a, b] * 1[N_{v,b} > 0]`, normalized to sum to 1
- force of infection:

```
lambda_i = susceptibility_i * (1 - protection_i) * beta
           * sum_l  c_l(a_i) * sum_b w_b * ( I_{v_l(i), b} / N_{v_l(i), b} )
P(infected today) = 1 - exp(-lambda_i)
```
- `I_{v,b}` = sum of `infectiousness_j * state_rel_infectiousness[state_j] * (1 - mask_effect_j)` over attending infectious agents in venue `v`, band `b`. Compute with `numpy.bincount` on the combined index `venue_id * n_bands + band` (weights = infectiousness load, then counts for `N_{v,b}`), then gather per agent. Cost is O(N) per layer per day, no pairwise lists.
- `protection_i` combines masking (when the agent chooses it), vaccination and prior immunity, using parameters from the DiseasePack and ScenarioPack.
- Closures zero or scale a layer for an area and time window (attendance masks).

### 4.2 Calibrating beta from R0
Starting guess from the next-generation matrix (Libin et al. 2020, supplement S2):
```
K = beta * M / gamma            R0 = (beta / gamma) * rho(M)
```
`rho` is the spectral radius (dominant eigenvalue). For a disease graph with several infectious states, replace `1/gamma` by the expected infectious duration weighted by relative infectiousness: `D = sum_s rel_inf_s * E[duration_s]`, and use `M_total = sum_l M^l`:
```
beta0 = R0 / ( rho(M_total) * D )
```
Then calibrate numerically in the agent model:
1. Create a fully susceptible copy of the population.
2. Seed `n` index cases (n of 50 or more, spread across the region); disable onward spread from anyone infected after day 0 (a flag).
3. Run until all index cases leave infectious states; count secondary infections `S`.
4. Estimate `R_hat = S / n`. Update `beta` by a secant step until `|R_hat - R0| / R0 < 0.02`.
5. Save the calibration report (beta0, final beta, R_hat, iterations, seeds).

### 4.3 State graph
The DiseasePack defines states, flags (`infectious`, `needs`, `absorbing`), relative infectiousness, transitions with age- and risk-dependent probabilities, and duration distributions (fixed, gamma, lognormal, Weibull; validate parameters). On entry to a state draw the duration; each day increment `days_in_state`; when it reaches the duration, draw the next state from the outgoing probabilities (vectorized with cumulative sums and `searchsorted`). Probabilities are adjusted per agent by `risk_multiplier` and the disease's vulnerability factors (section 5).

---

## 5. Disease-specific vulnerability and environment

### 5.1 Vulnerability factors (DiseasePack)
```yaml
vulnerability_factors:
  - id: <factor_id>                 # e.g. a condition relevant to THIS disease
    description: <text>
    effects:                        # multipliers or odds ratios, each with source/status
      susceptibility: <x>
      severity_odds: <x>            # applied to the logit of transitions toward worse states
      mortality_odds: <x>
      infectiousness: <x>
    region_field: <column in risk_factors.csv>
```
- The DiseasePack declares which factors matter for the disease (for a respiratory disease, respiratory conditions; for another disease, other factors such as malnutrition, immune suppression, pregnancy). The values come from sources or are `assumed`.
- The RegionPack supplies prevalence per age band, sex and area in `risk_factors.csv` (generalizes the old comorbidity file). If prevalence is missing for a declared factor, use a flagged placeholder.
- Population builder assigns each agent's factor bits using prevalence (with correlations between factors set by an optional correlation table, otherwise independent), then computes `risk_multiplier`.
- Apply effects on the logit scale: `logit(p') = logit(p) + sum_f bit_f * log(OR_f)`.

### 5.2 Environment and sanitation (RegionPack)
`environment.csv` per area: `safe_water_share`, `improved_sanitation_share`, `handwashing_facility_share`, `persons_per_room`, `informal_settlement_share`, `clean_cooking_share`, `green_space_share`, `climate_zone`, `season_profile` (optional), plus a free `extra` JSON column.
The DiseasePack declares `environment_modifiers`: which environment fields change which parameter (transmission in a layer, severity, duration) and by how much, each with source/status. If a disease declares none, these fields are stored but unused. Crowding (`persons_per_room`) can scale the household layer contact rate when the disease pack asks for it.
v1 still does not simulate vector or waterborne transmission; the environment modifiers are generic hooks, and `TransmissionModule` remains the extension point.

---

## 6. Generic resources and overflow

### 6.1 Resources are generic
No resource name (including oxygen) appears in `src/`. Resources are declared in packs:
```yaml
# RegionPack: resources.csv
resource_id, name, unit, area_id, date_or_static, nominal, effective_low, effective_high,
upper_cap_of_extra, restock_rate, source, status

# DiseasePack: states declare what they consume
- state: severe
  needs: {bed: general, other: {<resource_id>: <units per patient per day>}}
```
- Bed categories (`general`, `hdu`, `icu`, `icu_vent`) and any other resource (medicine stock, ventilators, oxygen, staff) are just resource IDs. Oxygen may appear in an example pack as one resource and nowhere else.
- A state that needs several resources is served only to the degree all are available (`service_level` in [0, 1] = min over needs of available / required); partial service is allowed.

### 6.2 Allocation
Daily: build demand by (area, resource), route each patient to the nearest area with free capacity (precomputed neighbor lists from area centroid distances, with travel delay and an optional inflow share from outside the region), decrement capacity, release by length of stay. Patients with `service_level < 1` are partially served; those with 0 are `unserved` that day, accumulating `unserved_days`.

### 6.3 Outcome for unserved or partially served patients
Not high mortality by default. A bed not being allocated does not imply death; the outcome depends on the individual.
For a patient in state `s` flagged `needs_care`:
```
logit(p_adverse) = logit(p_served_s)
                 + theta_0 * (1 - service_level)                # base effect of not being served
                 + theta_sev  * (severity_level_s - ref)
                 + theta_care * (1 - self_care_i)
                 + theta_sup  * (1 - support_i)
                 + theta_alt  * (1 - alt_care_access_i)
                 + theta_delay * unserved_days_i
```
- `p_adverse` is the probability of moving to the worse branch (for example death) instead of the recovery branch.
- `self_care_i` is derived from education, income band, health literacy proxy, prior experience with illness, caregiver presence, and compliance (compliance is one input, not the only one). `support_i` from household composition and caregiver availability. `alt_care_access_i` from distance to any provider and region-level home-care or tele-care availability.
- All `theta` values are config parameters with `status: assumed` unless sourced. `theta_0 = 0` is allowed and valid. Include them in sensitivity analysis. Mild states flagged `not needs_care` recover at home with their baseline probabilities.
- Report deaths attributable to overflow by comparing against a counterfactual run with unlimited resources (same seeds).

### 6.4 Additional resources and aids (what-if)
Scenario field:
```yaml
resource_adds:
  - resource_id: <id>
    area_id: <id or ALL>
    amount: <units>
    start_day: <d>
    delay_days: <d>          # procurement or setup delay
    ramp_days: <d>           # linear ramp to full amount
    duration_days: <d or null>
    cost_per_unit: <x>
```
- Enforce `amount <= upper_cap_of_extra` for that resource and area (from the region file); violations are an error with a clear message.
- Paired comparison: run baseline and variant with common random numbers and report deltas with confidence intervals: deaths, deaths attributable to overflow, unmet demand, days over capacity, equity gap, cost.
- `analysis/marginal_value.py`: sweep added units `k = 0, d, 2d, ...` per resource and per area (30 or more paired seeds each); report outcome versus units, the marginal benefit per extra unit, where it flattens (diminishing returns), and which area benefits most from the next unit. For a fixed budget of units, allocate greedily by marginal benefit across areas and check the result with an Optuna search.
- Studio gets an "Add resources" panel that builds this scenario and shows the delta report.

---

## 7. Rumor and misinformation layer

### 7.1 Social network
Sparse CSR adjacency `A` (scipy.sparse), built from layers: household ties (complete within household), workplace/school ties (sample `k` per agent from the venue), neighborhood ties (spatially clustered), weak ties (random within and across areas), and `n_influencers` high-degree accounts (power-law out-degree). Mass-media channel as broadcast to a fraction of agents per area per day. Degrees and weights are config, `assumed` unless sourced.

### 7.2 Rumor topics
`behavior.rumor.topics[]`: id, label, seed_area, seed_day, number of seeds, credibility, and `behavior_effects` (how belief changes mask use, vaccination acceptance, isolation, attendance). The claim label is for display; LLM policies see only the bucketed belief band.

### 7.3 Dynamics (vectorized, per topic k)
```
share_i(t)   ~ Bernoulli( sigmoid(g0 + g1*belief_ik + g2*share_propensity_i + g3*fear_i) )
exposure_i   = (A @ share_k)_i * credibility_k          # sparse matrix-vector product
belief_ik   += gullibility_i * (1 - trust_authority_i*tau) * (1 - belief_ik) * f(exposure_i)
              - correction_i(t) * efficacy * belief_ik   # fact-check or official correction
belief_ik    = clip(belief_ik, 0, 1)
```
- `f` is a saturating function (for example `1 - exp(-exposure)`). Optional backfire parameter (default 0, assumed).
- Correction campaigns: channel, start day, daily reach by area, efficacy. These are ScenarioPack interventions.
- Reference models to read and cite if used: Daley-Kendall and Maki-Thompson rumor models, and threshold or complex-contagion models. Verify before citing.

### 7.4 Effects on behavior
Belief lowers the probability of masking, vaccination acceptance, isolation, and workplace/market avoidance, via `behavior_effects`. Metrics: rumor reach by day, belief prevalence by area and group, and outcomes with versus without the rumor (counterfactual run, same seeds).

---

## 8. Compliance
```
compliance_i(t) = clip( base_i
                       + w_risk  * risk_perception_i(t)
                       + w_norm  * (share of ties complying)_i(t)
                       + w_enf   * enforcement_a(t)
                       - w_fat   * fatigue_i(t)
                       - sum_k  kappa_k * belief_ik , 0, 1 )
fatigue_i(t+1) = fatigue_i(t) + rate * (measure_active) - recovery * (no measure)
```
- `base_i` from traits and life history (`trust_authority`, `prior_authority_experience`, `conscientiousness`).
- Behavior policies (Rule, Jev, Gemini) output action probabilities; compliance modifies those probabilities (it does not replace them). Always sample actions, never argmax.
- Compliance is also one input to `self_care_i` (section 6.3).

---

## 9. Agent life histories
Each agent has a unique, structured history and routine, generated from marginals and conditional rules (config-driven, `assumed` unless sourced):
- **Life facts:** income band (conditional on occupation and area), household role, caregiver status, financial buffer (affects ability to isolate), chronic condition bits, prior infections and vaccination history, past bereavement, prior experience with authorities.
- **Routine template:** per occupation class (for example office worker, shift worker, student, homemaker, informal worker, retired), with persistent preferred venues (workplace, market, leisure, place of worship) so ties are stable across days.
- **Showcase agents (20 to 50):** a short biography generated by an LLM from these structured fields only (no invented facts), labeled GENERATED NARRATIVE. The biography never feeds the policy; only bucketed state does.
- Event log per showcase agent: state changes, decisions with probabilities, exposures.

---

## 10. Behavior policies and API contracts

### 10.1 Common
`DecisionPolicy.decide(situation, buckets) -> probabilities` per question. Sample from probabilities. Cache in SQLite keyed by (hash(bucket), hash(situation), question_set_version). Async with a semaphore (configurable concurrency). Fall back to `RulePolicy` on any failure and log the fallback rate. Never send raw records; only bucketed synthetic states.

### 10.2 Jev (TypeSafe AI)
- Endpoint `https://api.typesafe.ai/v1/systemone`; SDK `pip install typesafe-sdk`; key from env `TYPESAFE_API_KEY`; model alias `jev-latest`.
- Question types: Choice, Score, Noul (yes/no style). It returns probabilities and no reasoning. Question IDs are not sent to the model, so put every requirement in each question's instructions.
- Documentation and pricing change: read the current docs (docs.typesafe.ai) before implementing, measure real latency and rate limits with `check_apis.py`, and record them in `DATA_SOURCES.md`. Access routes other than a direct key (OpenRouter, Vercel AI Gateway, Cloudflare Workers AI) have been reported; test which one works for the user.
- Cost: published at $0.042 per million input tokens with output free (September 2026). Sources disagree on free credits (some report none, one reports a small signup credit, one reports a gateway credit), so do not count on free usage. With bucketed, cached calls the total cost for this project is cents, but Jev is paid and optional, never required.

### 10.2b Local logprob policy (free, default)
A free replacement for Jev-style typed decisions using any local instruction model.
1. Build each question as a prompt with 2 to 20 options labeled with single-token labels (A, B, C, ... ; Y/N for yes/no; 0 to 4 for scores). Put all instructions in the prompt and ask for the label only.
2. Call the model with one output token (`max_tokens=1`, Ollama `num_predict: 1`), `temperature=0`, thinking disabled, `logprobs=true`, and `top_logprobs` at least the number of options.
3. Probability of option k = exp(logprob of its label), normalized over the labels. If a label is missing from `top_logprobs`, assign a small floor before normalizing and log the miss.
4. Remove position bias: ask each question with 2 to 4 shuffled option orders and average the per-option probabilities after mapping labels back to options.
5. Cache by bucket like every other policy.

Engines: Ollama (use a version whose API returns logprobs on `/api/chat` or `/api/generate`; verify on the installed version), a llama.cpp server or vLLM through the OpenAI-compatible `/v1/chat/completions` with `logprobs` and `top_logprobs`, or in-process Hugging Face `transformers` reading next-token logits for the label tokens (no server; uses the RTX GPU).
Model choice: any small instruction-tuned open model that fits in GPU memory. Test two or three and keep the one whose answers are most consistent across option orders and prompt paraphrases. Check each model's license. Reasoning models must have thinking turned off, otherwise the first token is not the answer.
Caveats: raw token probabilities from a general model are not guaranteed to be calibrated and are sensitive to wording and option order. Run the prompt-sensitivity test (5 paraphrases), report the spread, and label results uncalibrated unless the user supplies labeled examples to check against.
Open-source libraries and at least one open model built around this single-token trick (choice, yes/no and score primitives) exist. Evaluate any of them for license, quality and GPU memory before use, and do not depend on them.

### 10.3 Gemini
- SDK `google-genai`; key `GEMINI_API_KEY`; model name `GEMINI_MODEL` from env (never hardcode). Used for the advisor (function calling), showcase explanations and biographies. Free-tier limits vary by model and change; implement exponential backoff on 429 and a configurable request budget per run.

### 10.4 OpenAI-compatible
`OPENAI_COMPAT_BASE_URL`, `OPENAI_COMPAT_API_KEY`, `OPENAI_COMPAT_MODEL` in `.env` for any compatible endpoint.

### 10.5 Key handling (important)
- The agent must never ask the user to type keys into chat. Provide `scripts/setup_keys.py`, which prompts locally with hidden input (`getpass`), writes `.env`, and never prints keys.
- `scripts/check_apis.py` prints a status table (service, reachable, latency, rate-limit headers if any) and never prints keys.
- `.env` is in `.gitignore`.

---

## 11. Metapopulation engine (from Libin et al. 2020, arXiv:2003.13676) 
A second, fast, area-level engine `engine_meta`. Uses: (a) cross-check of the agent engine; (b) fast screening of measures; (c) surrogate for optional RL. It is NOT the main engine.

### 11.1 Intra-area age-structured SEIR
For area `p`, age band `i`:
```
dS_i/dt = - phi_i S_i
dE_i/dt =   phi_i S_i - zeta E_i
dI_i/dt =   zeta E_i - gamma I_i
dR_i/dt =   gamma I_i
phi_i(t) = sum_j beta * M_ij(t) * I_j(t) / N_j(t)
N_i = S_i + E_i + I_i + R_i       (no births or deaths over short horizons)
```
`M_ij(t)` is time-dependent (layer switches model closures; the paper uses school-term versus holiday matrices). `zeta` is the latency rate and `gamma` the recovery rate. The paper used a latent period of 1 day and an infectious period of 1.8 days for influenza; those are not defaults here, take them from the DiseasePack.
- Stochastic version: the paper converts the ODEs to SDEs (Allen et al. 2008 procedure) and evaluates with Euler-Maruyama at daily steps. Acceptable equivalent: binomial chain, per area and band per day: `new_E ~ Bin(S, 1 - exp(-phi_i))`, `new_I ~ Bin(E, 1 - exp(-zeta))`, `new_R ~ Bin(I, 1 - exp(-gamma))`. If you use the binomial chain, say so.
- Collapse a multi-state disease graph to this SEIR form only for the meta engine, documenting the mapping.

### 11.2 Inter-area infection
Areas start uninfected except the seeded one. Uninfected area `p` becomes infected through a non-homogeneous Poisson process whose intensity depends on commuting flows:
```
phi_p(t) = sum_{p'} Mob[p', p] * beta * ( S^A_p(t) )^mu * Iinf_{p'}(t)
Iinf_{p'}(t) = I^A_{p'}(t) * M_AA
```
`Mob[p', p]` is the mobility flux from `p'` to `p` (commuting or the gravity model), `S^A` the susceptible adults, `I^A` the infectious adults, `M_AA` the adult-adult contact rate, and `mu` in [0, 1] a calibration parameter.
Time-scale transformation (Algorithm 2 of the paper), per uninfected area:
```
X ~ Exp(1)
each day t: compute phi_p(t); form the piecewise-linear intensity between daily values;
            Lambda(t) = cumulative integral of that intensity
            if Lambda(t) >= X:  infect area p (seed n_seed infectious adults);
                                 mark p infected (each area is infected once, as in the paper)
```
Complexity: only compute `phi_p` for uninfected areas from infected ones, `O(t * |P_infected| * |P_uninfected|)`, vectorized as a matrix-vector product.

### 11.3 Calibrating mu
The paper sets `mu = log(R0) * s` and fits `s` so the peak day of the patch model matches a homogeneous-mixing age-structured SEIR across a range of R0. Its fitted values (0.6 for the UK influenza setting, 2.74 for the 2009 pandemic fit) are specific to its data. Do not reuse them; fit `s` for each region and disease and report the fit. Also check that the attack rates of the two models are close (the paper found them nearly identical).

### 11.4 Cross-validation test (required)
With the same parameters and homogeneous mixing, the agent engine's aggregate curve should agree with the age-structured SEIR within configured tolerances (peak day, peak height, attack rate). Report the actual differences; do not tune tolerances to pass.

### 11.5 Performance
Paper reference: about 2 runs per second for 379 patches on a MacBook Pro using NumPy plus Numba. Use Numba for the area-evolution step if profiling shows a need.

### 11.6 Communities
Detect communities in the commuting graph (directed, weighted, edges where flux > 0) with the Leiden algorithm; check robustness by bootstrapping. Use the communities to group areas for coordinated policies, since deep multi-agent RL (and joint policy search) only scales to roughly 10 controlled areas at once.

---

## 12. Optimization and ground truth

### 12.1 Search
Optuna with `NSGAIISampler` over measure mix and timing; objectives = deaths, peak resource occupancy and days over capacity, unmet demand, cost proxy, equity gap. Evaluate each candidate on 10 or more paired seeds on the meta engine for screening, then re-evaluate the Pareto set on the agent engine with 30 or more seeds.

### 12.2 Exhaustive ground truth
For a small binary policy space (for example school closure open/closed for each of `w` weeks, and the epidemic spans at most about 25 weeks), enumerate every policy on the deterministic version of the model (remove the noise terms) and take the best. Compare each optimizer arm against it. For larger spaces, brute-force a coarse grid (for example 3 measures by 3 start times).

### 12.3 Optional PPO (last phase, only if asked)
Following Libin et al.:
- MDP: state = compartment values per controlled area (the paper used 16 values for four age groups of SEIR plus the remaining closure budget); action = open or close for the next week (binary per area; budget `b` of closure weeks, default `b in {2, 4, 6}`); transition = the epidemic model; reward = `-(S(s) - S(s'))`, the negative loss in susceptibles over the week (an attack-rate objective).
- Policy network output through a sigmoid gives the probability of keeping the measure off. A single-area PPO agent is trained first against the exhaustive ground truth. The multi-area version uses one "super-agent" with an output unit per area (input size = state size times number of areas), after grouping areas with Leiden.
- PPO hyperparameters the paper tuned (starting points, retune for your environment): 1024 local steps, batch size 128, clip epsilon 0.2, 24 epochs, entropy coefficient 0.0059, gamma 0.99, GAE lambda 0.95, one hidden layer of 20 tanh units, learning rate 0.002, Adam, gradient-norm clip 1.0. The paper used 10^4 episodes of 43 weeks for one district and 10^5 for the joint policy, and evaluated each learned policy by simulating it 1,000 times.
- Train on the meta engine (fast) and verify any learned policy on the agent engine. The paper warns that individual-based models make RL too slow and suggests learning a surrogate; that is what the meta engine is.
- Interpretability is limited; report that.

---

## 13. Validation and calibration
- Optional, only with user-supplied observed data. Without it, every report says UNCALIBRATED.
- Fit seeding, beta and compliance to observed cases with the policy timeline. Scale infections to reported cases with an ascertainment (reporting) factor that is fitted, not copied (the paper scaled by 1/4 for its 2009 influenza case). A good qualitative check from the paper: reproduce a double-peak epidemic caused by a seasonal or school-closure effect.
- Hold out a later period if available. Report failures honestly.
- Sensitivity: one-at-a-time and, if time allows, Sobol over R0, ascertainment, compliance parameters, rumor parameters, resource capacities, `theta` parameters in 6.3, and contact assumptions. State which recommendations change.

---

## 14. Testing
- **Invariants:** population conserved, no negative counts, absorbing states stay absorbing, probabilities in [0, 1], beliefs in [0, 1], capacity never negative, same seed reproduces results.
- **Statistical tests (not tautologies):** R0 calibration within 2%; more correction reach lowers mean belief (paired seeds); adding resources never increases unmet demand (paired seeds); `theta_0 = 0` leaves outcomes of unserved patients equal to the served baseline; cross-validation against the meta engine (11.4).
- **Mutation sanity check:** for five key tests, deliberately break the code and confirm the tests fail, then revert.
- **App tests:** `streamlit.testing.v1.AppTest` runs every Studio step headless with the synthetic region and fails on exceptions.
- Report the number of test files, test functions and the full pytest summary line in every walkthrough. "Passed" without output does not count.

---

## 15. Reference papers (verify before citing)
- Libin et al., Deep reinforcement learning for large-scale epidemic control, arXiv:2003.13676 (2020).
- Allen et al., Construction of equivalent stochastic differential equation models, Stochastic Analysis and Applications 26(2), 2008.
- Prem et al., synthetic contact matrices for many countries (2017, updated 2021).
- Levin et al., age-specific infection fatality rate meta-regression, Eur J Epidemiol 35:1123-1138 (2020).
- Liu et al., Simulating population compliance with pandemic interventions using LLMs, medRxiv preprint (2026, not peer reviewed): findings that LLM agents match average compliance but are too uniform and over-compliant, that models differ in bias, and that ensembling helps.

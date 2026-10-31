# EpiSwarm Studio: Assumptions Log (`ASSUMPTIONS.md`)

This file records all modeling assumptions, default parameter values, uncalibrated defaults, and structural assumptions used throughout EpiSwarm Studio.

In accordance with our **Honesty Rules**:
- Parameters lacking empirical citation are categorized as `assumed`.
- All runs without empirical user-supplied calibration data are explicitly flagged as **`UNCALIBRATED`**.
- The behavior layer (LLM decisions) carries a persistent **`Behavior layer unvalidated for this region`** status.
- Synthetic fixture data is designated **`SYNTHETIC DATA`** and is never presented as describing a real location.

---

## 1. Quick Region (L0) Synthetic Assumptions
When a user provides only aggregate (L0) inputs, the following assumptions are applied to synthesize lower-level tables:
1. **Household Distribution**: Poisson-like distribution centered on `avg_household_size` (default: 3.5), with rejection sampling ensuring at least one adult ($\ge 18$ years old) per household.
2. **Age Pyramids**: Default uniform or standardized UN 16-age band fallback when no specific country pyramid is supplied.
3. **Venues**: School capacity drawn from $\mathcal{N}(350, 75^2)$, workplace capacity drawn from lognormal distribution with mean 25, variance 10.
4. **Commute Gravity Model**: Commute flux between areas $i$ and $j$ follows gravity impedance:
   $$T_{ij} \propto \frac{P_i \cdot P_j}{(d_{ij} + \epsilon)^\alpha}$$
   with default assumed distance decay exponent $\alpha = 1.5$.
5. **Bed Allocation**: Hospital beds partitioned across wards/zones proportional to population unless specific hospital geolocation is provided. Default ICU ratio is assumed at 7% of total hospital beds.

---

## 2. Generic Disease Preset Assumptions (`respiratory_generic.yaml`)
1. **SEIR State Graph**:
   - Latent period: Gamma distribution ($\mu = 3.0$ days, $\sigma = 1.0$ day).
   - Infectious period: Gamma distribution ($\mu = 5.0$ days, $\sigma = 1.5$ days).
   - Asymptomatic fraction: 35% of infections are asymptomatic with relative infectiousness of 0.50.
2. **Transmission & Overdispersion**:
   - $R_0 = 2.50$ (calibrated numerically to match the spectral radius $\Upsilon(M)$ of the contact matrix).
   - Overdispersion parameter $k = 0.16$ (reflecting super-spreading phenomenon).
3. **Healthcare Overflow Multipliers**:
   - Mortality when needed general bed is unavailable: $2.0\times$ baseline case fatality.
   - Mortality when needed ICU bed is unavailable: $3.5\times$ baseline case fatality.
   - Mortality when medical oxygen buffer is depleted: $2.5\times$ baseline case fatality.
   - Compliance mitigation: Fully compliant agents receive a $0.85\times$ risk multiplier; non-compliant agents receive a $1.25\times$ multiplier.

---

## 3. Behavior Layer Assumptions
1. **Decision Triggers**: Agents evaluate protective decisions only upon specific trigger events:
   - Announcement of a new regional policy or intervention.
   - Area risk-band escalation.
   - Personal symptom onset or positive household member.
2. **Noise & Stochastic Choice**: Decisions are sampled probabilistically from model outputs; argmax selection is never enforced.
3. **Validation Status**: **Unvalidated**. LLM and rule-based behavioral adjustments represent hypothetical policy-response curves.

---

## 4. Sanitation Deficit Sensitivity
1. Areas with water access scores $< 0.50$ or high open drainage are assumed to exhibit a $1.15\times$ multiplier on domestic and community transmission rates for contact-sensitive pathogens.

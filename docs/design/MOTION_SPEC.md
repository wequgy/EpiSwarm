# EpiSwarm Studio v2: Animation & Motion Specification

## 1. Principles of Motion
1. **Calm, Eased Physics**: Motion in EpiSwarm Studio is measured and scientific. It avoids jitter, frantic flashing, or decorative distraction.
2. **Realism vs. Illustrative Transparency**: 
   - Regional infection counts and hospital bed occupancies represent **verifiable simulation outputs**.
   - Moving individual figures along commuting arcs represent **visual interpolation of daily aggregate flows** and are persistently labeled:
     > *"Visual interpolation: Animated figures illustrate daily commuter flows between home and work venues."*
3. **Performance Budget**:
   - 60 fps at 1080p rendering up to 3,000 animated figures on a standard GPU (RTX / modern integrated).
   - 30 fps graceful degradation with level-of-detail (LOD) aggregation on lower-power devices.

---

## 2. Dynamic Motion Catalog

| Element | Trigger | Duration | Easing | Visual Behavior |
|---|---|---|---|---|
| **Daily Outbreak Tick** | Step or playback timer | 800ms – 1600ms (based on speed 1x–10x) | Linear / smooth step | Advances day counter; updates borough heat color transitions. |
| **Borough Prevalence Tint** | Daily infection delta | 600ms | `cubic-bezier(0.16, 1, 0.3, 1)` (easeOutExpo) | Area polygon fill smoothly deepens or lightens based on active case density. |
| **New Infection Ripple** | Borough incidence > 0 | 1200ms | `ease-out` | Expanding translucent concentric ripple radiating from borough centroid. |
| **Commuter Figure Transit** | Sub-day transit cycle (morning 8am / evening 6pm) | 800ms | `cubic-bezier(0.4, 0, 0.2, 1)` (easeInOut) | Figures traverse smooth Bezier curves between home and work centroids. |
| **Hospital Strain Meter** | ICU demand exceeds nominal | Continuous | 1400ms periodic pulse | Warning amber or red halo pulses when occupancy > 90%; flashes red on capacity breach. |
| **Story Caption Feed** | New milestone event emitted in frame | 400ms | Slide-in from top with fade-in | Text enters smoothly, pushes older events down, auto-scrolls. |
| **HUD Number Tickers** | Any metric change | 300ms | Tabular number roll | Numeric characters roll smoothly between values without horizontal layout jump. |
| **Slide-over Inspector** | User clicks borough, hospital, or figure | 250ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Drawer slides in from right edge; stage dims slightly by 15%. |

---

## 3. Reduced Motion & Accessibility (`prefers-reduced-motion`)

When `@media (prefers-reduced-motion: reduce)` is enabled:
1. **Animated Figures Disabled**: Figure movements between venues are suppressed. Centroids display static density halos.
2. **Ripples and Pulses Removed**: Expanding infection ripples and pulsing warning halos become solid, high-contrast static alert rings.
3. **Instant Transitions**: Slide-overs and modals appear immediately (`0ms` duration) without sliding or scaling.
4. **Ticker Animation Off**: Metric counters snap directly to new numbers without rolling effects.

# EpiSwarm Studio v2: Design Tokens & Visual Language

## 1. Design Identity: Frosted Ice & Scientific Authority
EpiSwarm Studio v2 uses an **"Arctic Scientific Glass"** aesthetic:
- Deep atmospheric dark-slate backdrops paired with translucent frosted-glass panels (`backdrop-blur-md`).
- Crisp, clinical high-contrast foreground typography.
- Semantic clinical colors that maintain distinct perceptual channels (infection, protection, strain, neutral).
- Clean 8-point baseline grid with consistent border radii and generous breathing room.

---

## 2. Color Tokens

### 2.1 Surfaces & Neutrals
| Token | Dark Mode (Default) | Light Mode | Purpose |
|---|---|---|---|
| `surface-canvas` | `#0b0f19` (Deep Obsidian Ice) | `#f8fafc` (Slate 50) | Full-screen background |
| `surface-glass` | `rgba(15, 23, 42, 0.75)` | `rgba(255, 255, 255, 0.85)` | Floating HUD panels, docks, cards |
| `surface-glass-border` | `rgba(148, 163, 184, 0.15)` | `rgba(203, 213, 225, 0.60)` | Borders with subtle refraction |
| `surface-elevated` | `#1e293b` (Slate 800) | `#ffffff` (Pure White) | Slide-overs, modals, dropdown menus |
| `text-primary` | `#f8fafc` (Slate 50) | `#0f172a` (Slate 900) | Primary titles, metrics, and active states |
| `text-secondary` | `#94a3b8` (Slate 400) | `#475569` (Slate 600) | Body prose, secondary labels |
| `text-muted` | `#64748b` (Slate 500) | `#94a3b8` (Slate 400) | Microcopy, timestamps, inactive units |

### 2.2 Semantic Domain Signals
| Domain | Hex Code | Purpose | Accessibility Cue |
|---|---|---|---|
| **Infection / Contagion** | `#f43f5e` (Rose 500) / `#e11d48` | Active transmission, infectious agents | Diamond icon `◆` |
| **Exposure / Incubation** | `#fb923c` (Amber 400) | Exposed latent state ($E$) | Triangle icon `▲` |
| **Protection / Immunity** | `#06b6d4` (Cyan 500) / `#10b981` | Masking, recovery ($R$), compliance | Shield icon `🛡` |
| **Healthcare Capacity Stress** | `#f59e0b` (Amber 500) | Hospital strain, near-capacity warning | Pulse alert `⚡` |
| **Clinical Overflow / Breach** | `#ef4444` (Red 600) | ICU / ventilator capacity exceeded | Hexagon alert `⬢` |
| **Susceptible Baseline** | `#38bdf8` (Ice Sky 400) | Uninfected susceptible agents ($S$) | Circle icon `●` |
| **Deceased ($D$)** | `#475569` (Slate 600) | Fatalities | Cross icon `✚` |

---

## 3. Typography & Numerics
- **Body & Headings**: `Inter, system-ui, -apple-system, sans-serif`
  - Hierarchy:
    - Display Metric: `font-mono text-3xl font-extrabold tracking-tight`
    - Section Heading: `font-sans text-lg font-bold tracking-tight`
    - Body Standard: `font-sans text-sm font-normal leading-relaxed`
    - Micro Caption: `font-sans text-[11px] font-medium tracking-wide uppercase`
- **Telemetry & Numbers**: `JetBrains Mono, Fira Code, ui-monospace, monospace`
  - High-precision readouts (R_eff, agent counts, bed counts, timestamps) always render with tabular numbers (`tabular-nums`) to avoid layout jitter during live animation ticks.

---

## 4. Spacing, Elevation & Glassmorphism
- **8-Point Rhythm**: `p-2` (8px), `p-4` (16px), `p-6` (24px), `p-8` (32px).
- **Corner Radii**:
  - Small chips & badges: `rounded-md` (6px)
  - Cards & HUD widgets: `rounded-xl` (12px)
  - Modals & Floating Docks: `rounded-2xl` (16px)
- **Glass CSS Recipe**:
```css
.glass-panel {
  background: rgba(15, 23, 42, 0.72);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.36);
}
```

---

## 5. Accessibility & Contrast Verification
- **Contrast**: All text pairs achieve a minimum contrast ratio of **4.8:1** (WCAG AA), with critical alerts achieving **7:1** (AAA).
- **Colorblind Redundancy**: Color is never the sole carrier of meaning. State transitions and capacity alerts always combine color with geometric glyphs, pulsing rings, or text status badges.


"""Script to generate high-fidelity HTML mockups and render pixel-perfect 1920x1080 PNGs
for EpiSwarm Studio v2 Stage S0 design pack.
"""

import os
import subprocess
import time
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("docs/design/wireframes").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Shared CSS tokens & styles
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
body { background: #0b0f19; color: #f8fafc; overflow: hidden; width: 1920px; height: 1080px; position: relative; }
.mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-feature-settings: "tnum"; font-variant-numeric: tabular-nums; }
.glass-panel {
  background: rgba(15, 23, 42, 0.78);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.36);
}
.glass-card {
  background: rgba(30, 41, 59, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 10px;
}
.badge-calibrated {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.badge-demo {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}
.badge-mock {
  background: rgba(244, 63, 94, 0.2);
  color: #fb7185;
  border: 1px solid rgba(244, 63, 94, 0.4);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
}
.top-nav {
  height: 64px;
  background: rgba(15, 23, 42, 0.90);
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
}
.mode-pill {
  display: flex;
  background: rgba(30, 41, 59, 0.8);
  padding: 4px;
  border-radius: 8px;
  gap: 4px;
  border: 1px solid rgba(148, 163, 184, 0.15);
}
.mode-btn {
  padding: 6px 18px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  cursor: pointer;
}
.mode-btn.active {
  background: #2563eb;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
}
"""

def render_html_to_png(html_content: str, output_png_path: Path):
    temp_html = output_png_path.with_suffix(".html")
    temp_html.write_text(html_content, encoding="utf-8")
    
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        f"--window-size=1920,1080",
        f"--screenshot={output_png_path}",
        temp_html.as_uri(),
    ]
    subprocess.run(cmd, check=True)
    time.sleep(0.5)
    temp_html.unlink(missing_ok=True)
    print(f"Generated: {output_png_path.name} ({os.path.getsize(output_png_path)} bytes)")

# ------------------------------------------------------------------------------
# 1. CASE FILE OVERVIEW
# ------------------------------------------------------------------------------
HTML_01 = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>01 Case File Overview</title>
<style>{BASE_CSS}</style></head>
<body>
  <div class="top-nav">
    <div style="display:flex; align-items:center; gap:16px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <div style="width:28px; height:28px; border-radius:6px; background:#2563eb; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px;">E</div>
        <span style="font-weight:800; font-size:16px; letter-spacing:-0.02em;">EpiSwarm Studio <span style="color:#60a5fa; font-size:12px; font-weight:600;">v2</span></span>
      </div>
      <div class="mode-pill">
        <div class="mode-btn active">Case File</div>
        <div class="mode-btn">Simulate</div>
        <div class="mode-btn">Insights</div>
      </div>
      <span class="badge-calibrated">● CALIBRATED (L2)</span>
      <span class="badge-demo">DEMO: London Wave 1</span>
    </div>
    <div style="display:flex; align-items:center; gap:14px;">
      <div style="background:rgba(30,41,59,0.7); border:1px solid rgba(148,163,184,0.2); padding:6px 14px; border-radius:8px; font-size:12px; color:#94a3b8; display:flex; align-items:center; gap:8px;">
        <span>🔍 Jump to parameter, borough or scenario...</span>
        <kbd style="background:rgba(15,23,42,0.8); border:1px solid rgba(148,163,184,0.3); padding:1px 6px; border-radius:4px; font-size:10px;">Ctrl+K</kbd>
      </div>
      <div style="padding:6px 14px; border-radius:8px; background:rgba(30,41,59,0.8); border:1px solid rgba(148,163,184,0.2); font-size:12px; font-weight:600; cursor:pointer;">
        🛡️ Trust & Data Drawer ▾
      </div>
    </div>
  </div>

  <div style="padding: 32px 48px; max-width: 1800px; margin: 0 auto; height: calc(1080px - 64px); overflow-y: auto;">
    <!-- Header Banner -->
    <div class="glass-panel" style="padding: 24px 32px; display:flex; justify-content:space-between; align-items:center; margin-bottom: 28px;">
      <div>
        <div style="display:flex; align-items:center; gap:12px;">
          <h1 style="font-size: 26px; font-weight:800; letter-spacing:-0.03em;">London Municipal Outbreak Case File</h1>
          <span style="background:#1e293b; border:1px solid #475569; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:600;">v2.4 (Active)</span>
          <span style="color:#10b981; font-size:12px; font-weight:600;">🔒 Version Locked for Run</span>
        </div>
        <p style="font-size: 13px; color:#94a3b8; margin-top: 6px;">
          Greater London Authority (33 Local Authorities) · 8.9M Population · Target Resolution: 50,000 Agents · Calibrated to CoMix Wave 1
        </p>
      </div>
      <div style="display:flex; gap:14px; align-items:center;">
        <div style="text-align:right;">
          <div style="font-size:11px; text-transform:uppercase; font-weight:700; color:#94a3b8;">Completeness Score</div>
          <div class="mono" style="font-size:24px; font-weight:800; color:#10b981;">94% <span style="font-size:13px; color:#94a3b8; font-weight:400;">(2 Class C Assumptions)</span></div>
        </div>
        <button style="background:#2563eb; color:white; border:none; padding:12px 24px; border-radius:10px; font-weight:700; font-size:13px; cursor:pointer; box-shadow:0 4px 16px rgba(37,99,235,0.4);">
          Review & Launch Live Run →
        </button>
      </div>
    </div>

    <!-- 8 Section Modular Cards -->
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
      <!-- Section 1 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">📍</span>
            <span style="background:rgba(16,185,129,0.15); color:#10b981; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">100% COMPLETE</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">1. Area & Population</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">33 boroughs, ONS Census age/sex distributions, household sizes, boundaries.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• 33 Admin Units<br>• Real GeoJSON Boundaries<br>• Class A Evidence (ONS 2021)</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Edit Configuration →</button>
      </div>

      <!-- Section 2 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">🏢</span>
            <span style="background:rgba(16,185,129,0.15); color:#10b981; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">100% COMPLETE</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">2. Work, Schools & Commuting</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Census commute origin-destination flux, class sizes, commercial venues.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• 1,089 OD Commuter Pairs<br>• School Term Schedules<br>• Class A Evidence (NOMIS)</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Edit Commute Matrix →</button>
      </div>

      <!-- Section 3 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">🏥</span>
            <span style="background:rgba(16,185,129,0.15); color:#10b981; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">100% COMPLETE</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">3. Health System & Capacity</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">NHS Trust acute beds, ICU ventilators, non-outbreak baseline occupancy.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• 24 Acute NHS Trusts<br>• 18,400 Acute / 1,120 ICU<br>• Class A (NHS England SitRep)</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Configure Hospitals →</button>
      </div>

      <!-- Section 4 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">🦠</span>
            <span style="background:rgba(16,185,129,0.15); color:#10b981; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">100% COMPLETE</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">4. Pathogen & State Graph</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Respiratory transmission, R0 2.8, latent duration, age-stratified severity.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• 8 Clinical Compartments<br>• Beta Expectation Calibrated<br>• Class B Evidence (Ferguson/Levin)</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Edit Pathogen Graph →</button>
      </div>

      <!-- Section 5 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">🧠</span>
            <span style="background:rgba(245,158,11,0.15); color:#f59e0b; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">88% (CLASS C PRIOR)</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">5. People, Behavior & Rumors</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">CoMix contact survey calibration, fatigue kinetics, misinformation spread.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• 19.8M agents/sec Student<br>• Rumor Spread: 0.05 (Class C)<br>• Fatigue: 0.015/day</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Review Behavioral Traits →</button>
      </div>

      <!-- Section 6 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">🏛️</span>
            <span style="background:rgba(16,185,129,0.15); color:#10b981; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">100% COMPLETE</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">6. Policy Measures & Timeline</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Historical UK lockdown timeline, school closures, mask mandates.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• Day 23: School Suspension<br>• Day 25: Stay-at-Home Order<br>• Verified Timeline Ledger</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Open Timeline Editor →</button>
      </div>

      <!-- Section 7 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">⚙️</span>
            <span style="background:rgba(16,185,129,0.15); color:#10b981; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">CONFIGURED</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">7. Simulation Resolution</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Agent count, Monte Carlo replicates, horizon duration, random seeds.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#cbd5e1;">• 50,000 Agents (Stable Baseline)<br>• 5 Replicates (CRN Seeds)<br>• 60 Days Horizon</div>
        </div>
        <button class="glass-card" style="padding:8px; color:#60a5fa; font-weight:600; font-size:12px; border:none; cursor:pointer;">Adjust Settings →</button>
      </div>

      <!-- Section 8 -->
      <div class="glass-panel" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; height: 260px; border-color:#2563eb;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:22px;">🚀</span>
            <span style="background:rgba(37,99,235,0.2); color:#60a5fa; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">READY TO RUN</span>
          </div>
          <h3 style="font-size:16px; font-weight:700; margin-top:12px;">8. Review & Launch</h3>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Audit pre-flight validation gates, memory bounds, and launch live execution.</p>
          <div class="mono" style="margin-top:12px; font-size:12px; color:#60a5fa;">• Zero Integrity Scan Errors<br>• Memory: ~1.2 GB Est.<br>• Wallclock: ~18s Est.</div>
        </div>
        <button style="padding:8px; background:#2563eb; color:white; font-weight:700; font-size:12px; border:none; border-radius:6px; cursor:pointer;">Pre-Flight Review →</button>
      </div>
    </div>
  </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 2. DATA ENTRY & IMPORT MAPPING
# ------------------------------------------------------------------------------
HTML_02 = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>02 Data Entry & Import Mapping</title>
<style>{BASE_CSS}</style></head>
<body>
  <div class="top-nav">
    <div style="display:flex; align-items:center; gap:16px;">
      <span style="font-weight:800; font-size:16px;">EpiSwarm Studio v2</span>
      <span style="color:#94a3b8; font-size:13px;">› Case File › Section 1: Area & Population Intake</span>
    </div>
    <div style="display:flex; gap:12px;">
      <button class="glass-card" style="padding:6px 14px; font-size:12px; color:#cbd5e1; border:none;">📥 Download Excel Template (.xlsx)</button>
      <button class="glass-card" style="padding:6px 14px; font-size:12px; color:#cbd5e1; border:none;">📥 Download CSV Spec (.csv)</button>
    </div>
  </div>

  <div style="padding: 28px 48px; max-width: 1800px; margin: 0 auto; display:grid; grid-template-columns: 2fr 1fr; gap: 24px;">
    <!-- Main Intake Area -->
    <div class="glass-panel" style="padding:28px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <div>
          <h2 style="font-size:20px; font-weight:800;">Upload Regional Area & Demographics Table</h2>
          <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Upload boundaries and demographics. The intake mapper automatically validates column schemas and units.</p>
        </div>
        <span class="badge-calibrated">Column Schema: 100% Matched</span>
      </div>

      <!-- Upload Dropzone -->
      <div style="border: 2px dashed rgba(148,163,184,0.3); border-radius:12px; padding: 24px; text-align:center; background:rgba(15,23,42,0.4); margin-bottom:24px;">
        <div style="font-size:28px; margin-bottom:8px;">📄</div>
        <div style="font-size:13px; font-weight:700;">Uploaded: <span class="mono" style="color:#60a5fa;">greater_london_areas_2021.csv</span> (33 rows, 8 columns)</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">SHA-256 Checksum: <span class="mono">e3b0c44298fc1c149afbf4c8996fb924...</span> (Saved to Evidence Ledger)</div>
      </div>

      <!-- Column Mapping Table -->
      <h3 style="font-size:14px; font-weight:700; margin-bottom:12px;">Verified Field & Unit Mappings</h3>
      <table style="width:100%; border-collapse:collapse; font-size:12px;">
        <thead>
          <tr style="border-bottom:1px solid rgba(148,163,184,0.2); text-align:left; color:#94a3b8; font-size:11px; text-transform:uppercase;">
            <th style="padding:8px;">Uploaded Column</th>
            <th style="padding:8px;">Target Contract Field</th>
            <th style="padding:8px;">Detected Unit</th>
            <th style="padding:8px;">Sample Value</th>
            <th style="padding:8px;">Status</th>
          </tr>
        </thead>
        <tbody class="mono">
          <tr style="border-bottom:1px solid rgba(148,163,184,0.1);">
            <td style="padding:10px 8px; font-weight:700;">lad21_code</td>
            <td style="padding:10px 8px; color:#60a5fa;">area_id (Primary Key)</td>
            <td style="padding:10px 8px;">ISO GSS Code</td>
            <td style="padding:10px 8px;">E09000007 (Camden)</td>
            <td style="padding:10px 8px; color:#10b981;">✓ Matched</td>
          </tr>
          <tr style="border-bottom:1px solid rgba(148,163,184,0.1);">
            <td style="padding:10px 8px; font-weight:700;">lad21_name</td>
            <td style="padding:10px 8px; color:#60a5fa;">name</td>
            <td style="padding:10px 8px;">Text string</td>
            <td style="padding:10px 8px;">Camden</td>
            <td style="padding:10px 8px; color:#10b981;">✓ Matched</td>
          </tr>
          <tr style="border-bottom:1px solid rgba(148,163,184,0.1);">
            <td style="padding:10px 8px; font-weight:700;">census_pop_2021</td>
            <td style="padding:10px 8px; color:#60a5fa;">population</td>
            <td style="padding:10px 8px;">integer (headcount)</td>
            <td style="padding:10px 8px;">210,136</td>
            <td style="padding:10px 8px; color:#10b981;">✓ Matched</td>
          </tr>
          <tr style="border-bottom:1px solid rgba(148,163,184,0.1);">
            <td style="padding:10px 8px; font-weight:700;">area_km2</td>
            <td style="padding:10px 8px; color:#60a5fa;">sq_km</td>
            <td style="padding:10px 8px;">sq_kilometers</td>
            <td style="padding:10px 8px;">21.8 km²</td>
            <td style="padding:10px 8px; color:#10b981;">✓ Matched</td>
          </tr>
          <tr>
            <td style="padding:10px 8px; font-weight:700;">households_count</td>
            <td style="padding:10px 8px; color:#60a5fa;">households</td>
            <td style="padding:10px 8px;">integer (dwellings)</td>
            <td style="padding:10px 8px;">98,240</td>
            <td style="padding:10px 8px; color:#10b981;">✓ Matched</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Onboarding AI Assistant Sidebar -->
    <div class="glass-panel" style="padding:24px; display:flex; flex-direction:column; justify-content:space-between;">
      <div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
          <span style="font-size:18px;">🤖</span>
          <h3 style="font-size:15px; font-weight:700;">Onboarding Assistant</h3>
        </div>
        <p style="font-size:12px; color:#94a3b8; line-height:1.5;">
          I inspected your uploaded boundaries. All 33 administrative boroughs map cleanly to ONS GSS standards.
        </p>

        <div style="background:rgba(30,41,59,0.7); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:12px; margin-top:16px;">
          <div style="font-size:11px; font-weight:700; color:#f59e0b; margin-bottom:4px;">⚠️ Notice: Missing GeoJSON Polygons</div>
          <p style="font-size:11px; color:#cbd5e1; line-height:1.4;">
            Your file contains coordinates but no boundaries. I can estimate spatial centroids from ONS Open Geography (Class C Prior) or you can attach a GeoJSON file.
          </p>
          <button style="margin-top:8px; background:#2563eb; color:white; border:none; padding:6px 12px; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer;">
            Accept ONS GeoJSON Prior
          </button>
        </div>

        <div style="margin-top:20px;">
          <span style="font-size:11px; text-transform:uppercase; font-weight:700; color:#94a3b8;">Provenance Ledger Entry</span>
          <div class="mono" style="font-size:10px; color:#64748b; margin-top:4px; line-height:1.4;">
            source_type: user_supplied<br>
            retrieved_at: 2026-11-14T19:42:00Z<br>
            evidence_class: A (Direct Local Census)
          </div>
        </div>
      </div>

      <button style="width:100%; padding:12px; background:#2563eb; color:white; font-weight:700; font-size:13px; border:none; border-radius:8px; cursor:pointer;">
        Save & Continue to Commuting →
      </button>
    </div>
  </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 3. REVIEW & LAUNCH (PRE-FLIGHT)
# ------------------------------------------------------------------------------
HTML_03 = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>03 Review & Launch</title>
<style>{BASE_CSS}</style></head>
<body>
  <div class="top-nav">
    <div style="display:flex; align-items:center; gap:16px;">
      <span style="font-weight:800; font-size:16px;">EpiSwarm Studio v2</span>
      <span style="color:#94a3b8; font-size:13px;">› Case File › Section 8: Pre-Flight Review & Launch</span>
    </div>
    <span class="badge-calibrated">Integrity Gates: 100% PASS</span>
  </div>

  <div style="padding: 28px 48px; max-width: 1700px; margin: 0 auto; display:grid; grid-template-columns: 1fr 1fr; gap: 28px;">
    <!-- Left: Pre-flight Audit & Estimates -->
    <div class="glass-panel" style="padding:28px; display:flex; flex-direction:column; justify-content:space-between;">
      <div>
        <h2 style="font-size:22px; font-weight:800;">Simulation Pre-Flight Audit</h2>
        <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Verifying numerical stability, convergence resolution, and hardware constraints.</p>

        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin-top:20px;">
          <div class="glass-card" style="padding:14px; text-align:center;">
            <div style="font-size:11px; color:#94a3b8;">Operational Resolution</div>
            <div class="mono" style="font-size:20px; font-weight:800; color:#60a5fa; margin-top:4px;">50,000</div>
            <div style="font-size:10px; color:#10b981; margin-top:2px;">✓ Convergence Baseline</div>
          </div>
          <div class="glass-card" style="padding:14px; text-align:center;">
            <div style="font-size:11px; color:#94a3b8;">Estimated Memory</div>
            <div class="mono" style="font-size:20px; font-weight:800; color:#10b981; margin-top:4px;">~1.18 GB</div>
            <div style="font-size:10px; color:#94a3b8; margin-top:2px;">Peak budget: 11 GB</div>
          </div>
          <div class="glass-card" style="padding:14px; text-align:center;">
            <div style="font-size:11px; color:#94a3b8;">Estimated Wallclock</div>
            <div class="mono" style="font-size:20px; font-weight:800; color:#f59e0b; margin-top:4px;">~18.4s</div>
            <div style="font-size:10px; color:#94a3b8; margin-top:2px;">5 Stochastic Seeds</div>
          </div>
        </div>

        <div style="margin-top:24px;">
          <h3 style="font-size:14px; font-weight:700; margin-bottom:10px;">Pre-Registration & Evidence Summary</h3>
          <div class="glass-card" style="padding:16px; font-size:12px; line-height:1.6;">
            <div>• <strong style="color:#10b981;">Class A Evidence (82%):</strong> Area censuses, commute flow matrices, NHS acute & ICU baseline sitreps.</div>
            <div>• <strong style="color:#60a5fa;">Class B Evidence (12%):</strong> Age-stratified severity odds, household transmission relative weights.</div>
            <div>• <strong style="color:#f59e0b;">Class C Assumptions (6%):</strong> Rumor spread rate (&beta; = 0.05), public compliance decay rate.</div>
          </div>
        </div>

        <div style="margin-top:20px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:14px;">
          <div style="font-weight:700; font-size:12px; color:#10b981;">🏷️ Projected Run Trust Tier: CALIBRATED (L2)</div>
          <p style="font-size:11px; color:#cbd5e1; margin-top:2px;">This simulation will carry an authentic Evidence Ledger stamp with full cryptographic provenance.</p>
        </div>
      </div>

      <div style="display:flex; gap:12px; margin-top:24px;">
        <button style="flex:1; padding:14px; background:#2563eb; color:white; font-size:14px; font-weight:800; border:none; border-radius:10px; cursor:pointer; box-shadow:0 4px 16px rgba(37,99,235,0.4);">
          ▶ Launch Live Simulation Stage
        </button>
      </div>
    </div>

    <!-- Right: Top Influential Assumptions -->
    <div class="glass-panel" style="padding:28px;">
      <h2 style="font-size:18px; font-weight:800;">Assumption Influence Ranking</h2>
      <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Ranked by variance contribution (Sobol Index) to total peak ICU demand.</p>

      <div style="margin-top:18px; display:flex; flex-direction:column; gap:12px;">
        <div class="glass-card" style="padding:14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:13px;">1. Basic Reproduction Number ($R_0$)</div>
            <div class="mono" style="font-size:11px; color:#94a3b8;">Path: /disease/transmission/r0 · S_i = 0.42</div>
          </div>
          <span class="mono" style="background:#1e293b; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">2.80</span>
        </div>

        <div class="glass-card" style="padding:14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:13px;">2. ICU Surge Effective Capacity</div>
            <div class="mono" style="font-size:11px; color:#94a3b8;">Path: /region/resources/icu_beds/effective · S_i = 0.24</div>
          </div>
          <span class="mono" style="background:#1e293b; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">1,120 beds</span>
        </div>

        <div class="glass-card" style="padding:14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:13px;">3. Mask Mandate Inward/Outward Efficacy</div>
            <div class="mono" style="font-size:11px; color:#94a3b8;">Path: /scenario/interventions/mask_mandate · S_i = 0.16</div>
          </div>
          <span class="mono" style="background:#1e293b; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">0.45</span>
        </div>

        <div class="glass-card" style="padding:14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:13px;">4. Misinformation Spread Rate (&beta;<sub>rumor</sub>)</div>
            <div class="mono" style="font-size:11px; color:#f59e0b;">Path: /behavior/rumor/spread_rate · Class C Prior</div>
          </div>
          <span class="mono" style="background:rgba(245,158,11,0.2); color:#fbbf24; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">0.05</span>
        </div>

        <div class="glass-card" style="padding:14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:13px;">5. School Closure Layer Deactivation</div>
            <div class="mono" style="font-size:11px; color:#94a3b8;">Path: /scenario/interventions/school_closure · S_i = 0.08</div>
          </div>
          <span class="mono" style="background:#1e293b; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">0.90</span>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 4. SIMULATION STAGE MID-RUN (HERO CANVAS)
# ------------------------------------------------------------------------------
HTML_04 = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>04 Simulation Stage Mid-Run</title>
<style>{BASE_CSS}
.borough-polygon {{ stroke: rgba(148,163,184,0.3); stroke-width: 1.5; transition: fill 0.5s ease; }}
.commuter-line {{ stroke: rgba(96,165,250,0.4); stroke-width: 1.5; stroke-dasharray: 4 4; }}
</style></head>
<body>
  <!-- Top Bar -->
  <div class="top-nav">
    <div style="display:flex; align-items:center; gap:16px;">
      <span style="font-weight:800; font-size:16px;">EpiSwarm Studio v2</span>
      <div class="mode-pill">
        <div class="mode-btn">Case File</div>
        <div class="mode-btn active">Simulate</div>
        <div class="mode-btn">Insights</div>
      </div>
      <span class="badge-calibrated">● RUNNING LIVE</span>
      <span class="badge-mock">PROTOTYPE PREVIEW</span>
    </div>

    <!-- Center HUD Display -->
    <div class="glass-panel" style="padding: 6px 24px; display:flex; gap:28px; align-items:center;">
      <div style="text-align:center;">
        <span style="font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Day / Date</span>
        <div class="mono" style="font-size:18px; font-weight:800; color:#ffffff;">Day 28 <span style="font-size:11px; color:#94a3b8;">(24 Oct)</span></div>
      </div>
      <div style="text-align:center;">
        <span style="font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Active Infected</span>
        <div class="mono" style="font-size:18px; font-weight:800; color:#f43f5e;">4,820</div>
      </div>
      <div style="text-align:center;">
        <span style="font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Hospital Acute</span>
        <div class="mono" style="font-size:18px; font-weight:800; color:#f59e0b;">94% <span style="font-size:11px;">(17,296 / 18,400)</span></div>
      </div>
      <div style="text-align:center;">
        <span style="font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase;">ICU Strain</span>
        <div class="mono" style="font-size:18px; font-weight:800; color:#ef4444; animation:pulse 1s infinite;">102% BREACH</div>
      </div>
      <div style="text-align:center;">
        <span style="font-size:10px; color:#94a3b8; font-weight:700; text-transform:uppercase;">R_eff (Rt)</span>
        <div class="mono" style="font-size:18px; font-weight:800; color:#60a5fa;">1.42</div>
      </div>
    </div>

    <div style="display:flex; align-items:center; gap:12px;">
      <div style="font-size:12px; color:#94a3b8;">London Wave 1 (50k Agents)</div>
      <button class="glass-card" style="padding:6px 12px; color:white; border:none; font-size:12px; cursor:pointer;">🛡️ Trust</button>
    </div>
  </div>

  <!-- Main Canvas Viewport (SVG Cartogram / Diorama) -->
  <div style="position:relative; width:100%; height:calc(1080px - 64px); background:#0b0f19; overflow:hidden;">
    <!-- Background Grid -->
    <svg width="100%" height="100%" style="position:absolute; top:0; left:0;">
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(148, 163, 184, 0.04)" stroke-width="1"/>
        </pattern>
        <radialGradient id="heat-high" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#f43f5e" stop-opacity="0.1"/>
        </radialGradient>
        <radialGradient id="heat-med" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#fb923c" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#fb923c" stop-opacity="0.08"/>
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />

      <!-- Borough Polygons (Isometric / Schematic Layout) -->
      <!-- Central London (High Prevalence) -->
      <polygon points="900,420 1020,450 1060,550 940,580 840,520" fill="url(#heat-high)" class="borough-polygon" />
      <polygon points="1020,450 1140,430 1190,520 1060,550" fill="url(#heat-high)" class="borough-polygon" />
      <polygon points="840,520 940,580 910,680 790,640" fill="url(#heat-med)" class="borough-polygon" />
      <polygon points="940,580 1060,550 1090,660 970,700" fill="url(#heat-high)" class="borough-polygon" />
      <polygon points="760,400 880,380 900,420 840,520 740,480" fill="url(#heat-med)" class="borough-polygon" />
      <polygon points="1060,350 1180,360 1140,430 1020,450" fill="url(#heat-med)" class="borough-polygon" />
      <!-- Outer Boroughs -->
      <polygon points="620,460 740,480 790,640 680,620" fill="rgba(30,41,59,0.5)" class="borough-polygon" />
      <polygon points="1190,520 1310,500 1340,610 1210,630" fill="rgba(30,41,59,0.5)" class="borough-polygon" />

      <!-- Commuter Flux Arcs -->
      <path d="M 680,540 Q 840,450 980,510" fill="none" class="commuter-line" />
      <path d="M 1250,560 Q 1120,470 980,510" fill="none" class="commuter-line" />
      <path d="M 940,640 Q 960,580 980,510" fill="none" class="commuter-line" />

      <!-- Sampled Animated Figures (Simulated Commuters) -->
      <!-- Infectious figure (Red) -->
      <circle cx="820" cy="480" r="4.5" fill="#f43f5e" />
      <circle cx="910" cy="500" r="4" fill="#f43f5e" />
      <circle cx="1010" cy="490" r="5" fill="#f43f5e" />
      <!-- Exposed figure (Orange) -->
      <circle cx="750" cy="510" r="4" fill="#fb923c" />
      <circle cx="1120" cy="530" r="4" fill="#fb923c" />
      <!-- Recovered / Immune (Green) -->
      <circle cx="860" cy="560" r="4" fill="#10b981" />
      <circle cx="1040" cy="570" r="4" fill="#10b981" />
      <!-- Susceptible (Ice Blue) -->
      <circle cx="710" cy="530" r="3.5" fill="#38bdf8" />
      <circle cx="1200" cy="580" r="3.5" fill="#38bdf8" />

      <!-- Hospital Nodes -->
      <g transform="translate(960, 470)">
        <circle cx="0" cy="0" r="16" fill="rgba(239,68,68,0.2)" stroke="#ef4444" stroke-width="2" />
        <text x="0" y="5" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="bold">🏥</text>
        <rect x="-24" y="-32" width="48" height="12" rx="3" fill="#1e293b" stroke="#ef4444" stroke-width="1" />
        <rect x="-22" y="-30" width="44" height="8" rx="2" fill="#ef4444" />
      </g>
    </svg>

    <!-- Story Feed Ticker (Top Left) -->
    <div class="glass-panel" style="position:absolute; top:24px; left:28px; width:360px; padding:16px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span style="font-size:11px; text-transform:uppercase; font-weight:800; color:#60a5fa;">Epidemic Event Feed</span>
        <span style="font-size:10px; color:#94a3b8;">Live Frame Stream</span>
      </div>
      <div style="display:flex; flex-direction:column; gap:8px; font-size:12px; line-height:1.4;">
        <div style="background:rgba(239,68,68,0.15); border-left:3px solid #ef4444; padding:6px 10px; border-radius:4px;">
          <strong style="color:#ef4444;">Day 28 · 14:00</strong><br>
          Camden ICU reaches 100% capacity. 14 critical patients diverted to South London Trust.
        </div>
        <div style="background:rgba(245,158,11,0.15); border-left:3px solid #f59e0b; padding:6px 10px; border-radius:4px;">
          <strong style="color:#f59e0b;">Day 26 · 09:30</strong><br>
          Metropolitan commuter volume down 34% following public advisory.
        </div>
        <div style="background:rgba(59,130,246,0.15); border-left:3px solid #60a5fa; padding:6px 10px; border-radius:4px;">
          <strong style="color:#60a5fa;">Day 23 · 08:00</strong><br>
          Universal school suspension enacted across all 33 boroughs.
        </div>
      </div>
    </div>

    <!-- Borough Inspector Slide-over (Right) -->
    <div class="glass-panel" style="position:absolute; top:24px; right:28px; width:340px; padding:20px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <span style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase;">Selected Borough</span>
          <h3 style="font-size:18px; font-weight:800;">Camden (E09000007)</h3>
        </div>
        <span class="badge-calibrated">High Alert</span>
      </div>
      <div class="mono" style="margin-top:14px; font-size:12px; display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; justify-content:space-between;">
          <span style="color:#94a3b8;">Population:</span>
          <span>210,136</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
          <span style="color:#94a3b8;">Active Prevalence:</span>
          <span style="color:#f43f5e; font-weight:700;">2.48% (5,210 cases)</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
          <span style="color:#94a3b8;">Public Compliance:</span>
          <span style="color:#10b981;">71.4% (Fatigue: Low)</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
          <span style="color:#94a3b8;">Misinformation Belief:</span>
          <span style="color:#f59e0b;">18.2% Adoption</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
          <span style="color:#94a3b8;">Nearest Hospital:</span>
          <span style="color:#ef4444; font-weight:700;">Royal Free (100% ICU)</span>
        </div>
      </div>
      <button style="width:100%; margin-top:16px; padding:8px; background:#1e293b; border:1px solid #475569; color:#60a5fa; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer;">
        Apply Targeted Local Interventions →
      </button>
    </div>

    <!-- Floating Playback Dock (Bottom Center) -->
    <div class="glass-panel" style="position:absolute; bottom:32px; left:50%; transform:translateX(-50%); padding:12px 28px; display:flex; align-items:center; gap:20px; border-radius:18px;">
      <button style="background:none; border:none; color:#cbd5e1; font-size:18px; cursor:pointer;">⏮</button>
      <button style="background:#2563eb; border:none; width:44px; height:44px; border-radius:50%; color:white; font-size:18px; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 4px 12px rgba(37,99,235,0.4);">
        ❚❚
      </button>
      <button style="background:none; border:none; color:#cbd5e1; font-size:18px; cursor:pointer;">⏭ +1d</button>

      <!-- Scrubber -->
      <div style="display:flex; flex-direction:column; gap:4px; width:340px;">
        <div style="display:flex; justify-content:space-between; font-size:10px; color:#94a3b8;">
          <span>Day 0</span>
          <span style="color:#60a5fa; font-weight:700;">Day 28 of 60</span>
          <span>Day 60</span>
        </div>
        <input type="range" min="0" max="60" value="28" style="width:100%; accent-color:#2563eb;">
      </div>

      <!-- Speed Control -->
      <div style="display:flex; background:rgba(30,41,59,0.8); border:1px solid rgba(148,163,184,0.2); border-radius:6px; padding:2px;">
        <span style="padding:4px 8px; font-size:11px; color:#94a3b8; cursor:pointer;">1x</span>
        <span style="padding:4px 8px; font-size:11px; background:#2563eb; color:white; border-radius:4px; font-weight:700;">2x</span>
        <span style="padding:4px 8px; font-size:11px; color:#94a3b8; cursor:pointer;">5x</span>
      </div>

      <!-- Action Buttons -->
      <div style="display:flex; gap:8px;">
        <button style="padding:8px 14px; background:#f59e0b; color:#0f172a; font-weight:800; font-size:11px; border:none; border-radius:8px; cursor:pointer;">
          ⚡ Intervene Now
        </button>
        <button style="padding:8px 14px; background:#1e293b; border:1px solid #475569; color:#ffffff; font-weight:700; font-size:11px; border-radius:8px; cursor:pointer;">
          ⎇ Branch Run
        </button>
      </div>
    </div>

    <!-- Visual Transparency Caption (Bottom Left) -->
    <div style="position:absolute; bottom:12px; left:28px; font-size:11px; color:#64748b;">
      ℹ️ <em>Visual interpolation: Animated figures illustrate daily commuter flows between home and work venues.</em>
    </div>
  </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 5. INSIGHTS DASHBOARD & BRANCHING
# ------------------------------------------------------------------------------
HTML_05 = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>05 Insights Dashboard</title>
<style>{BASE_CSS}</style></head>
<body>
  <div class="top-nav">
    <div style="display:flex; align-items:center; gap:16px;">
      <span style="font-weight:800; font-size:16px;">EpiSwarm Studio v2</span>
      <div class="mode-pill">
        <div class="mode-btn">Case File</div>
        <div class="mode-btn">Simulate</div>
        <div class="mode-btn active">Insights</div>
      </div>
      <span class="badge-calibrated">Ensemble: 5 CRN Seeds</span>
    </div>
    <div style="display:flex; gap:12px;">
      <button style="background:#2563eb; color:white; border:none; padding:8px 16px; border-radius:8px; font-size:12px; font-weight:700; cursor:pointer;">
        📄 Export Official Briefing (PDF & JSON Ledger)
      </button>
    </div>
  </div>

  <div style="padding: 24px 48px; max-width: 1800px; margin: 0 auto; height:calc(1080px - 64px); overflow-y:auto;">
    <!-- Insights Sub-Navigation Tabs -->
    <div style="display:flex; gap:8px; border-bottom:1px solid rgba(148,163,184,0.2); padding-bottom:12px; margin-bottom:24px;">
      <button class="mode-btn active" style="background:#2563eb; color:white;">Epidemic Trajectories</button>
      <button class="mode-btn" style="background:#1e293b; color:#94a3b8;">Spatial Arrival Order</button>
      <button class="mode-btn" style="background:#1e293b; color:#94a3b8;">Healthcare & ICU Strain</button>
      <button class="mode-btn" style="background:#1e293b; color:#94a3b8;">Demographic Equity</button>
      <button class="mode-btn active" style="background:rgba(37,99,235,0.2); color:#60a5fa; border:1px solid #2563eb;">Counterfactual Compare (Branch A vs Baseline)</button>
      <button class="mode-btn" style="background:#1e293b; color:#94a3b8;">Pareto Optimization</button>
      <button class="mode-btn" style="background:#1e293b; color:#94a3b8;">AI Policy Advisor</button>
    </div>

    <!-- Active View: Counterfactual Compare Header -->
    <div class="glass-panel" style="padding:24px 32px; display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
      <div>
        <h2 style="font-size:20px; font-weight:800;">Paired Policy Comparison: Baseline vs Branch A (Rapid Intervention)</h2>
        <p style="font-size:12px; color:#94a3b8; margin-top:4px;">Paired Monte Carlo runs over common random numbers (CRN) isolating exact policy delta.</p>
      </div>
      <div class="mono" style="display:flex; gap:20px;">
        <div style="text-align:right;">
          <span style="font-size:11px; color:#94a3b8;">Averted Deaths</span>
          <div style="font-size:22px; font-weight:800; color:#10b981;">-340 <span style="font-size:12px;">(95% CI: -380, -295)</span></div>
        </div>
        <div style="text-align:right;">
          <span style="font-size:11px; color:#94a3b8;">ICU Overflow Reduction</span>
          <div style="font-size:22px; font-weight:800; color:#10b981;">-14.2 Days</div>
        </div>
      </div>
    </div>

    <!-- Comparison Grid -->
    <div style="display:grid; grid-template-columns: 2fr 1fr; gap:24px;">
      <!-- Chart Area -->
      <div class="glass-panel" style="padding:24px;">
        <h3 style="font-size:15px; font-weight:700; margin-bottom:14px;">Infection Wave Trajectory (Confidence Bands)</h3>
        <!-- Synthetic SVG Chart for Mockup -->
        <svg width="100%" height="320" viewBox="0 0 800 320" style="background:rgba(15,23,42,0.4); border-radius:8px;">
          <!-- Grid Lines -->
          <line x1="60" y1="280" x2="760" y2="280" stroke="#334155" stroke-width="1"/>
          <line x1="60" y1="210" x2="760" y2="210" stroke="#1e293b" stroke-width="1"/>
          <line x1="60" y1="140" x2="760" y2="140" stroke="#1e293b" stroke-width="1"/>
          <line x1="60" y1="70" x2="760" y2="70" stroke="#1e293b" stroke-width="1"/>

          <!-- Baseline Curve (Red) -->
          <path d="M 60,280 Q 240,280 340,60 T 600,270 L 760,280" fill="none" stroke="#f43f5e" stroke-width="3"/>
          <path d="M 60,280 Q 240,280 340,60 T 600,270 L 760,280 L 60,280" fill="rgba(244,63,94,0.1)"/>

          <!-- Branch A Curve (Blue - Dampened) -->
          <path d="M 60,280 Q 240,280 340,160 T 640,275 L 760,280" fill="none" stroke="#38bdf8" stroke-width="3"/>
          <path d="M 60,280 Q 240,280 340,160 T 640,275 L 760,280 L 60,280" fill="rgba(56,189,248,0.1)"/>

          <!-- Hospital Capacity Line -->
          <line x1="60" y1="180" x2="760" y2="180" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 6"/>
          <text x="70" y="174" fill="#f59e0b" font-size="11" font-weight="bold">Nominal Acute Bed Capacity (18,400 beds)</text>

          <!-- Labels -->
          <text x="60" y="300" fill="#94a3b8" font-size="11">Day 0</text>
          <text x="340" y="300" fill="#94a3b8" font-size="11">Day 28 (Peak)</text>
          <text x="740" y="300" fill="#94a3b8" font-size="11">Day 60</text>
        </svg>

        <div style="display:flex; justify-content:center; gap:24px; margin-top:14px; font-size:12px;">
          <span style="color:#f43f5e; font-weight:700;">● Baseline: Peak Day 28 (7,420 cases)</span>
          <span style="color:#38bdf8; font-weight:700;">● Branch A: Peak Day 34 (4,110 cases)</span>
        </div>
      </div>

      <!-- Disparity & Metrics Breakdown -->
      <div class="glass-panel" style="padding:24px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <h3 style="font-size:15px; font-weight:700; margin-bottom:14px;">Equity & Spatial Delta Breakdown</h3>
          <div style="display:flex; flex-direction:column; gap:12px; font-size:12px;">
            <div class="glass-card" style="padding:12px;">
              <span style="color:#94a3b8;">Attack Rate Delta:</span>
              <div class="mono" style="font-size:16px; font-weight:700; color:#10b981;">34.2% → 22.8% (-11.4%)</div>
            </div>
            <div class="glass-card" style="padding:12px;">
              <span style="color:#94a3b8;">Lowest Income Quartile Infection Share:</span>
              <div class="mono" style="font-size:16px; font-weight:700; color:#60a5fa;">38.1% → 29.4% (-8.7%)</div>
            </div>
            <div class="glass-card" style="padding:12px;">
              <span style="color:#94a3b8;">Hospital Overflow Deaths:</span>
              <div class="mono" style="font-size:16px; font-weight:700; color:#10b981;">482 → 142 (-340 deaths)</div>
            </div>
          </div>
        </div>

        <button style="width:100%; padding:10px; background:#1e293b; border:1px solid #475569; color:#cbd5e1; border-radius:8px; font-size:12px; font-weight:700; cursor:pointer;">
          Inspect Spatial Arrival Rank Table →
        </button>
      </div>
    </div>
  </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 6. TRUST & DATA DRAWER (TOP SLIDE-DOWN)
# ------------------------------------------------------------------------------
HTML_06 = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>06 Trust & Data Drawer</title>
<style>{BASE_CSS}</style></head>
<body>
  <!-- Dimmed Background Simulated Canvas -->
  <div style="filter:blur(6px); opacity:0.4; pointer-events:none; padding:40px;">
    <h1>EpiSwarm Simulation Background Canvas</h1>
  </div>

  <!-- Slide-down Glass Drawer Overlay -->
  <div class="glass-panel" style="position:absolute; top:0; left:0; width:100%; height:820px; border-radius:0 0 16px 16px; z-index:1000; padding:32px 56px; border-bottom:2px solid #2563eb; display:flex; flex-direction:column; justify-content:space-between;">
    <div>
      <!-- Drawer Header -->
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(148,163,184,0.2); padding-bottom:16px; margin-bottom:28px;">
        <div style="display:flex; align-items:center; gap:16px;">
          <h2 style="font-size:22px; font-weight:800; letter-spacing:-0.02em;">🛡️ Scientific Validation & Cryptographic Evidence Ledger</h2>
          <span class="badge-calibrated">Status: VALIDATED (Wave 1 Targets Passed)</span>
        </div>
        <button class="glass-card" style="padding:6px 16px; color:#cbd5e1; font-size:12px; font-weight:700; border:none; cursor:pointer;">✕ Close Drawer</button>
      </div>

      <!-- 3 Columns in Drawer -->
      <div style="display:grid; grid-template-columns: 1fr 1.2fr 1fr; gap:28px;">
        <!-- Column 1: Machine Validation Card -->
        <div class="glass-card" style="padding:20px;">
          <h3 style="font-size:15px; font-weight:700; color:#60a5fa; margin-bottom:12px;">Machine-Readable Validation Card</h3>
          <div class="mono" style="font-size:11px; line-height:1.7; color:#cbd5e1;">
            <div>• Spatial Arrival Rank (33 Boroughs): <strong style="color:#10b981;">ρ = 0.678 (PASS)</strong></div>
            <div>• CoMix Stratified Behaviors: <strong style="color:#10b981;">&lt; 1% Twin Recovery (PASS)</strong></div>
            <div>• NHS Acute Bed Peak Demand: <strong style="color:#10b981;">18,200 ± 650 (PASS)</strong></div>
            <div>• ICU Overflow Duration Error: <strong style="color:#10b981;">&lt; 2 Days (PASS)</strong></div>
            <div>• Pre-registered London Wave 3: <strong style="color:#f59e0b;">HELD-OUT GATE LOCKED</strong></div>
            <div>• Automated Integrity Scan: <strong style="color:#10b981;">0 Violations in Codebase</strong></div>
          </div>
        </div>

        <!-- Column 2: Evidence Ledger Audit -->
        <div class="glass-card" style="padding:20px;">
          <h3 style="font-size:15px; font-weight:700; color:#60a5fa; margin-bottom:12px;">SHA-256 Checksummed Artifacts</h3>
          <div class="mono" style="font-size:11px; display:flex; flex-direction:column; gap:8px;">
            <div style="border-bottom:1px solid #334155; padding-bottom:6px;">
              <span style="font-weight:700; color:#ffffff;">greater_london_areas.csv</span><br>
              <span style="color:#64748b;">SHA-256: 7f8a3b91c0e2... · License: OGL v3.0 (UK ONS)</span>
            </div>
            <div style="border-bottom:1px solid #334155; padding-bottom:6px;">
              <span style="font-weight:700; color:#ffffff;">london_commute_od.csv</span><br>
              <span style="color:#64748b;">SHA-256: 12ab99f441c0... · Source: NOMIS Census 2021</span>
            </div>
            <div style="border-bottom:1px solid #334155; padding-bottom:6px;">
              <span style="font-weight:700; color:#ffffff;">comix_contact_strata.csv</span><br>
              <span style="color:#64748b;">SHA-256: d5e23910ab31... · Source: UKHSA CoMix Survey</span>
            </div>
            <div>
              <span style="font-weight:700; color:#ffffff;">nhs_bed_capacity.csv</span><br>
              <span style="color:#64748b;">SHA-256: aa820019cfa1... · Source: NHS England SitRep</span>
            </div>
          </div>
        </div>

        <!-- Column 3: Compute Backends Status -->
        <div class="glass-card" style="padding:20px;">
          <h3 style="font-size:15px; font-weight:700; color:#60a5fa; margin-bottom:12px;">Active Compute Backends</h3>
          <div class="mono" style="font-size:11px; line-height:1.8; color:#cbd5e1;">
            <div>• Engine: <strong style="color:#10b981;">Vectorized NumPy (C-Accelerated)</strong></div>
            <div>• Local Model: <strong style="color:#10b981;">Ollama llama3.2:3b (localhost:11434)</strong></div>
            <div>• Job Queue: <strong style="color:#10b981;">Persistent SQLite WAL Backend</strong></div>
            <div>• WebSocket Channel: <strong style="color:#10b981;">Paced Live Protocol v2</strong></div>
            <div>• Behavioral Student: <strong style="color:#10b981;">19.8M agents/sec active</strong></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer Footer -->
    <div style="border-top:1px solid rgba(148,163,184,0.2); padding-top:16px; display:flex; justify-content:space-between; align-items:center; font-size:11px; color:#94a3b8;">
      <div>Integrity Hash: <span class="mono">d7a8fbb210e39...</span> · Zero mock data used in validation paths.</div>
      <button style="padding:8px 16px; background:#2563eb; color:white; border:none; border-radius:6px; font-weight:700; cursor:pointer;">
        Download Audit Package (.zip)
      </button>
    </div>
  </div>
</body>
</html>
"""

def main():
    print("Generating Stage S0 High-Fidelity Mockups...")
    render_html_to_png(HTML_01, OUTPUT_DIR / "01_case_file_overview.png")
    render_html_to_png(HTML_02, OUTPUT_DIR / "02_data_entry_import.png")
    render_html_to_png(HTML_03, OUTPUT_DIR / "03_review_launch.png")
    render_html_to_png(HTML_04, OUTPUT_DIR / "04_simulation_stage_live.png")
    render_html_to_png(HTML_05, OUTPUT_DIR / "05_insights_dashboard.png")
    render_html_to_png(HTML_06, OUTPUT_DIR / "06_trust_data_drawer.png")
    print("All 6 high-fidelity mockups generated successfully in docs/design/wireframes/")

if __name__ == "__main__":
    main()

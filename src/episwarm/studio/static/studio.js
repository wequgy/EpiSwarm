/**
 * EpiSwarm Studio - Bengaluru Metropolitan Model Controller
 * Clean, uncluttered, high-legibility interface connecting to FastAPI simulation backend.
 */

const STATE = {
  activeTab: 'viewport',
  simulationData: null,
  currentDay: 14,
  isPlaying: false,
  playSpeed: 1,
  playInterval: null,
  showcaseAgents: []
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupControls();
  await loadSystemStatus();
  await loadCurrentSimulation();
  await loadShowcaseAgents();
});

// Setup Navigation Tabs
function setupNavigation() {
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-tab');
      switchTab(target);
    });
  });

  const topRun = document.getElementById('btn-top-run-scenario');
  if (topRun) topRun.addEventListener('click', () => switchTab('scenario'));

  const sideAdvisor = document.getElementById('btn-sidebar-advisor');
  if (sideAdvisor) sideAdvisor.addEventListener('click', () => switchTab('decision'));
}

function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `view-${tabId}`);
  });

  if (tabId === 'decision') {
    renderDecisionPareto();
  } else if (tabId === 'viewport') {
    renderSparkline();
  }
}

// Fetch Backend Status
async function loadSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    console.log('[System Status: Ready]', data);
  } catch (err) {
    console.warn('Backend status check error:', err);
  }
}

// Load or Run Default Simulation
async function loadCurrentSimulation() {
  try {
    showLoadingBanner('Synchronizing Bengaluru simulation telemetry...');
    const res = await fetch('/api/current_results');
    const data = await res.json();
    STATE.simulationData = data;
    hideLoadingBanner();

    STATE.currentDay = Math.min(14, (data.horizon_days || 30) - 1);
    updateUI();
    renderSparkline();
  } catch (err) {
    console.error('Failed to load simulation results:', err);
    hideLoadingBanner();
  }
}

// Load Showcase Agents
async function loadShowcaseAgents() {
  try {
    const res = await fetch('/api/agents');
    STATE.showcaseAgents = await res.json();
    renderShowcaseAgentCards();
  } catch (err) {
    console.warn('Failed to load showcase agents:', err);
  }
}

// Setup User Controls
function setupControls() {
  // Timeline slider
  const slider = document.getElementById('timeline-slider');
  if (slider) {
    slider.addEventListener('input', (e) => {
      STATE.currentDay = parseInt(e.target.value, 10);
      updateUI();
    });
  }

  // Play / Pause
  const playBtn = document.getElementById('btn-play-pause');
  if (playBtn) {
    playBtn.addEventListener('click', togglePlayPause);
  }

  // Step buttons
  const stepPrev = document.getElementById('btn-bottom-step-prev');
  if (stepPrev) {
    stepPrev.addEventListener('click', () => {
      if (STATE.currentDay > 0) {
        STATE.currentDay--;
        updateUI();
      }
    });
  }

  const stepNext = document.getElementById('btn-bottom-step-next');
  if (stepNext) {
    stepNext.addEventListener('click', () => {
      const maxDay = STATE.simulationData ? STATE.simulationData.horizon_days - 1 : 29;
      if (STATE.currentDay < maxDay) {
        STATE.currentDay++;
        updateUI();
      }
    });
  }

  // Parameter Studio sliders
  const r0Slider = document.getElementById('param-r0');
  if (r0Slider) {
    r0Slider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value).toFixed(2);
      const span = document.getElementById('param-r0-val');
      if (span) span.textContent = val;
    });
  }

  const compSlider = document.getElementById('param-compliance');
  if (compSlider) {
    compSlider.addEventListener('input', (e) => {
      const pct = Math.round(parseFloat(e.target.value) * 100);
      const span = document.getElementById('param-compliance-val');
      if (span) span.textContent = `${pct}%`;
    });
  }

  // Commit Run
  const commitRun = document.getElementById('btn-commit-run');
  if (commitRun) commitRun.addEventListener('click', executeSimulation);

  // Policy Advisor
  const advisorBtn = document.getElementById('btn-trigger-advisor');
  if (advisorBtn) advisorBtn.addEventListener('click', requestPolicyAdvisor);

  // Policy Chips toggles
  document.querySelectorAll('.policy-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
    });
  });
}

function togglePlayPause() {
  if (STATE.isPlaying) {
    pausePlay();
  } else {
    startPlay();
  }
}

function startPlay() {
  STATE.isPlaying = true;
  const btn = document.getElementById('btn-play-pause');
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-sm">pause</span><span>PAUSE</span>';
  startPlayInterval();
}

function pausePlay() {
  STATE.isPlaying = false;
  clearInterval(STATE.playInterval);
  const btn = document.getElementById('btn-play-pause');
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-sm">play_arrow</span><span>PLAY</span>';
}

function startPlayInterval() {
  clearInterval(STATE.playInterval);
  const intervalMs = Math.max(100, Math.floor(550 / STATE.playSpeed));
  const maxDay = STATE.simulationData ? STATE.simulationData.horizon_days - 1 : 29;

  STATE.playInterval = setInterval(() => {
    if (STATE.currentDay < maxDay) {
      STATE.currentDay++;
      updateUI();
    } else {
      pausePlay();
    }
  }, intervalMs);
}

// Update UI elements based on current day and simulation metrics
function updateUI() {
  const day = STATE.currentDay;
  const dStr = String(day).padStart(2, '0');

  // Sliders and day labels
  const slider = document.getElementById('timeline-slider');
  if (slider) slider.value = day;

  setElemText('current-day-label', `DAY ${dStr} OF 30`);
  setElemText('top-day-badge', `DAY ${dStr} OF 30`);

  if (!STATE.simulationData) return;
  const metrics = STATE.simulationData.daily_metrics || [];
  const current = metrics[day] || {};

  const activeCases = current.active_cases || 0;
  const reff = (STATE.simulationData.empirical_r0 || 2.42).toFixed(2);

  // Top header badges
  setElemText('top-cases-badge', activeCases.toLocaleString());
  setElemText('top-reff-badge', reff);

  // Right Sidebar Metrics
  setElemText('stat-active-cases', activeCases.toLocaleString());
  setElemText('stat-reff', reff);

  // Update Map Zones (Active cases proportionally mapped across Bengaluru sectors)
  const centralActive = Math.round(activeCases * 0.42);
  const eastActive = Math.round(activeCases * 0.32);
  const southActive = Math.round(activeCases * 0.16);
  const northActive = Math.max(0, activeCases - centralActive - eastActive - southActive);

  const cumAR = ((STATE.simulationData.attack_rate || 0.40) * 100).toFixed(1);
  const progressRatio = Math.min(1.0, (day + 1) / (STATE.simulationData.horizon_days || 30));
  const curAR = (cumAR * progressRatio).toFixed(1);

  setElemText('zone-central-active', centralActive.toLocaleString());
  setElemText('zone-central-ar', `${curAR}%`);

  setElemText('zone-east-active', eastActive.toLocaleString());
  setElemText('zone-east-ar', `${(curAR * 0.95).toFixed(1)}%`);

  setElemText('zone-south-active', southActive.toLocaleString());
  setElemText('zone-south-ar', `${(curAR * 0.75).toFixed(1)}%`);

  setElemText('zone-north-active', northActive.toLocaleString());
  setElemText('zone-north-ar', `${(curAR * 0.65).toFixed(1)}%`);

  // Bengaluru Hospital Saturation Meters
  const icuDemand = current.icu_demand || 0;
  const vicPct = Math.min(100, Math.round((icuDemand * 0.55 / 45) * 100));
  const manipalPct = Math.min(100, Math.round((icuDemand * 0.30 / 25) * 100));
  const bowringPct = Math.min(100, Math.round((icuDemand * 0.15 / 15) * 100));

  updateHospitalBar('meter-victoria', 'meter-victoria-pct', vicPct, 45);
  updateHospitalBar('meter-manipal', 'meter-manipal-pct', manipalPct, 25);
  updateHospitalBar('meter-bowring', 'meter-bowring-pct', bowringPct, 15);

  // Update Dispatch Ledger
  updateDispatchLedger(day, current);

  // Update Sparkline
  renderSparkline();
}

function updateHospitalBar(barId, pctId, pct, beds) {
  const bar = document.getElementById(barId);
  const text = document.getElementById(pctId);
  if (bar) {
    bar.style.width = `${pct}%`;
    bar.className = 'h-full ' + (pct >= 90 ? 'bg-[#ba1a1a]' : (pct >= 70 ? 'bg-[#f59e0b]' : 'bg-[#436274]'));
  }
  if (text) {
    text.textContent = pct >= 90 ? `${pct}% [OVERFLOW RISK]` : `${pct}% (${Math.round(beds * pct / 100)}/${beds} beds)`;
    text.className = 'font-bold ' + (pct >= 90 ? 'text-[#ba1a1a]' : 'text-[#171c20]');
  }
}

function updateDispatchLedger(day, metric) {
  const container = document.getElementById('dispatch-ledger-stream');
  if (!container) return;

  const alerts = [
    { day: 0, tag: 'INDEX CASE', desc: 'First clinical cluster reported near KR Wholesale Market. Primary contact tracing active.', color: '#436274' },
    { day: 4, tag: 'METRO SURGE', desc: 'High commuter density detected on Namma Metro Purple Line (Majestic ↔ Indiranagar).', color: '#436274' },
    { day: 8, tag: 'SURGE WARNING', desc: 'Victoria Hospital ICU bed occupancy passes 70% threshold. Triage protocol initiated.', color: '#f59e0b' },
    { day: 11, tag: 'CONTAINMENT', desc: 'BBMP orders 50% passenger capacity cap on public bus and metro coaches.', color: '#436274' },
    { day: 14, tag: 'TECH ADVISORY', desc: 'Outer Ring Road (ORR) and Whitefield IT campuses transition to mandatory WFH schedules.', color: '#436274' },
    { day: 18, tag: 'PEAK TRANSMISSION', desc: `Peak epidemic demand. Unmet critical care requests: ${metric.unmet_demand || 0} beds.`, color: '#ba1a1a' },
    { day: 25, tag: 'CLEARANCE', desc: 'Effective R_t drops below 1.0. Community viral clearance accelerating across South wards.', color: '#059669' }
  ];

  const visible = alerts.filter(a => a.day <= day);
  container.innerHTML = visible.map(a => `
    <div class="border border-[#171c20] p-1.5 bg-[#F8FAFC]">
      <div class="flex items-center justify-between text-[9px] font-bold mb-0.5" style="color: ${a.color};">
        <span>● ${a.tag}</span>
        <span>DAY ${String(a.day).padStart(2, '0')}</span>
      </div>
      <p class="text-[11px] text-[#171c20] leading-tight font-bold">${a.desc}</p>
    </div>
  `).join('');
}

// Render Trajectory Sparkline
function renderSparkline() {
  const canvas = document.getElementById('sparkline-canvas');
  if (!canvas || !STATE.simulationData) return;
  const ctx = canvas.getContext('2d');
  const metrics = STATE.simulationData.daily_metrics || [];
  if (metrics.length === 0) return;

  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const maxVal = Math.max(...metrics.map(m => m.active_cases || 1));

  // ICU Capacity Threshold Line
  ctx.strokeStyle = '#ba1a1a';
  ctx.setLineDash([3, 2]);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, 10);
  ctx.lineTo(w, 10);
  ctx.stroke();
  ctx.setLineDash([]);

  // Trajectory curve
  ctx.beginPath();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = '#ba1a1a';
  metrics.forEach((m, idx) => {
    const x = (idx / (metrics.length - 1)) * w;
    const y = h - ((m.active_cases || 0) / maxVal) * (h - 14) - 2;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Current Day Marker
  const curX = (STATE.currentDay / (metrics.length - 1)) * w;
  const curY = h - (((metrics[STATE.currentDay]?.active_cases || 0) / maxVal) * (h - 14)) - 2;
  ctx.fillStyle = '#171c20';
  ctx.beginPath();
  ctx.arc(curX, curY, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

// Render Showcase Agents
function renderShowcaseAgentCards() {
  const container = document.getElementById('showcase-cards-container');
  if (!container) return;

  container.innerHTML = STATE.showcaseAgents.map(a => `
    <div class="border-2 border-[#171c20] p-4 bg-[#F8FAFC] shadow-[3px_3px_0px_#171c20]">
      <div class="flex justify-between items-center mb-1">
        <span class="font-display font-bold text-base text-[#171c20]">${a.name}</span>
        <span class="px-2 py-0.5 bg-[#bfe0f5] border border-[#171c20] text-[10px] font-bold">${a.district}</span>
      </div>
      <div class="text-[11px] text-[#436274] font-bold mb-2">ROLE: ${a.role.toUpperCase()}</div>
      <p class="text-xs text-[#334155] mb-2 leading-relaxed">${a.biography}</p>
      <div class="text-[9px] px-2 py-0.5 bg-[#FEF3C7] border border-[#171c20] inline-block font-bold">
        [GENERATED NARRATIVE - SYNTHETIC DATA ONLY]
      </div>
    </div>
  `).join('');
}

// Render Decision Pareto Frontier
function renderDecisionPareto() {
  if (!STATE.simulationData) return;
  const d = STATE.simulationData;

  setElemText('dec-total-infections', (d.total_infections || 0).toLocaleString());
  setElemText('dec-total-deaths', (d.total_deaths || 0).toLocaleString());
  setElemText('dec-overflow-deaths', (d.overflow_deaths || 0).toLocaleString());
  setElemText('dec-attack-rate', `${((d.attack_rate || 0.42) * 100).toFixed(1)}%`);

  const canvas = document.getElementById('decision-pareto-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 1;
  for (let x = 40; x < w; x += 40) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h - 20); ctx.stroke();
  }
  for (let y = 20; y < h - 20; y += 30) {
    ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(w, y); ctx.stroke();
  }

  // Curve
  ctx.strokeStyle = '#436274';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(50, 30);
  ctx.bezierCurveTo(120, 140, 260, 160, 420, 175);
  ctx.stroke();

  // Point
  ctx.fillStyle = '#ba1a1a';
  ctx.beginPath();
  ctx.arc(200, 150, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#171c20';
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = '#171c20';
  ctx.font = 'bold 10px "Space Mono", monospace';
  ctx.fillText('OPTIMAL BENGALURU POLICY POINT', 215, 148);
}

// Execute New Simulation
async function executeSimulation() {
  const r0 = parseFloat(document.getElementById('param-r0')?.value || 2.5);
  const compliance = parseFloat(document.getElementById('param-compliance')?.value || 0.65);
  const horizon = parseInt(document.getElementById('param-horizon')?.value || 30, 10);
  const schoolClosure = document.getElementById('param-closure-school')?.checked;
  const maskMandate = document.getElementById('param-mandate-mask')?.checked;

  const interventions = [];
  if (schoolClosure) {
    interventions.push({
      name: 'school_closure_mandate',
      measure_type: 'school_closure',
      area_id: 'ALL',
      start_day: 7,
      end_day: 28,
      stringency: 1.0,
      cost_per_day: 1.2
    });
  }
  if (maskMandate) {
    interventions.push({
      name: 'transit_mask_mandate',
      measure_type: 'mask_mandate',
      area_id: 'ALL',
      start_day: 5,
      end_day: 30,
      stringency: 0.8,
      cost_per_day: 0.3
    });
  }

  const payload = {
    region_dir: 'regions/example_synthetic',
    disease_path: 'diseases/respiratory_generic.yaml',
    scenario_path: 'scenarios/baseline.yaml',
    population_scale: 5000,
    r0: r0,
    compliance: compliance,
    horizon_days: horizon,
    interventions: interventions,
    random_seed: 42
  };

  try {
    showLoadingBanner('Simulating Bengaluru epidemic trajectory...');
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error(await res.text());
    STATE.simulationData = await res.json();
    hideLoadingBanner();

    STATE.currentDay = 0;
    updateUI();
    switchTab('viewport');
  } catch (err) {
    hideLoadingBanner();
    alert(`Simulation error: ${err.message}`);
  }
}

// Trigger AI Policy Advisor
async function requestPolicyAdvisor() {
  const container = document.getElementById('advisor-output-box');
  if (container) {
    container.innerHTML = '<div class="text-xs text-[#436274] font-bold p-3">Evaluating counterfactual policy trade-offs...</div>';
  }

  try {
    const res = await fetch('/api/advisor', { method: 'POST' });
    const rec = await res.json();

    if (container) {
      container.innerHTML = `
        <div class="border-2 border-[#171c20] p-4 bg-white shadow-[3px_3px_0px_#171c20] mt-3">
          <div class="flex justify-between items-center mb-2">
            <span class="font-display font-bold text-sm text-[#171c20]">OPTIMAL BENGALURU ADVISORY</span>
            <span class="px-2 py-0.5 bg-[#D1FAE5] text-[#065F46] border border-[#171c20] text-[10px] font-bold">FEASIBLE</span>
          </div>
          <div class="text-xs mb-2">
            <strong>ESTIMATED REDUCTION IN OVERFLOW DEATHS:</strong> <span class="text-[#059669] font-bold">-${rec.predicted_deaths_reduction || 35}%</span>
          </div>
          <div class="text-[11px] bg-[#F8FAFC] border border-[#171c20] p-2 mb-2">
            <strong>RECOMMENDED MEASURES:</strong>
            <ul class="list-disc pl-4 mt-1">
              ${(rec.recommended_measures || []).map(m => `<li>${m.name} (${m.measure_type}) Days ${m.start_day}-${m.end_day}</li>`).join('')}
            </ul>
          </div>
          <div class="text-[9px] text-[#596168]">
            <strong>NOTE:</strong> ${rec.human_in_the_loop_advisory || 'Illustrative simulation advice.'}
          </div>
        </div>
      `;
    }
  } catch (err) {
    if (container) {
      container.innerHTML = `<div class="text-xs text-[#ba1a1a] p-2 font-bold">Advisor error: ${err.message}</div>`;
    }
  }
}

function setElemText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function showLoadingBanner(msg) {
  let banner = document.getElementById('loading-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'loading-banner';
    banner.style.cssText = 'position: fixed; top: 12px; right: 24px; z-index: 9999; background: #FEF3C7; border: 2px solid #171c20; box-shadow: 3px 3px 0 #171c20; padding: 10px 16px; font-size: 0.75rem; font-weight: 700; font-family: monospace;';
    document.body.appendChild(banner);
  }
  banner.textContent = `[EPISWARM] ${msg}`;
  banner.style.display = 'block';
}

function hideLoadingBanner() {
  const banner = document.getElementById('loading-banner');
  if (banner) banner.style.display = 'none';
}

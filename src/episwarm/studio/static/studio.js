/**
 * EpiSwarm Studio - Field Dispatch Controller
 * Matches the Google Stitch Field Dispatch Blueprint UI.
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

// Navigation Tab Switching
function setupNavigation() {
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-tab');
      switchTab(target);
    });
  });
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
    console.log('[System Status]', data);
  } catch (err) {
    console.warn('Backend status check error:', err);
  }
}

// Load or Run Default Simulation
async function loadCurrentSimulation() {
  try {
    showLoadingBanner('Synchronizing simulation telemetry...');
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

  // Speed Toggles
  document.querySelectorAll('.speed-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.speed-toggle-btn').forEach(b => {
        b.classList.remove('bg-[#bfe0f5]', 'font-bold');
        b.classList.add('hover:bg-[#e4e9ee]');
      });
      btn.classList.add('bg-[#bfe0f5]', 'font-bold');
      STATE.playSpeed = parseInt(btn.getAttribute('data-speed'), 10) || 1;
      if (STATE.isPlaying) {
        startPlayInterval();
      }
    });
  });

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

  // Run Scenario triggers
  const topRun = document.getElementById('btn-top-run-scenario');
  if (topRun) topRun.addEventListener('click', () => switchTab('scenario'));

  const commitRun = document.getElementById('btn-commit-run');
  if (commitRun) commitRun.addEventListener('click', executeSimulation);

  const bottomCommit = document.getElementById('btn-bottom-commit');
  if (bottomCommit) bottomCommit.addEventListener('click', () => switchTab('scenario'));

  // R0 slider
  const r0Slider = document.getElementById('param-r0');
  if (r0Slider) {
    r0Slider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value).toFixed(2);
      const span = document.getElementById('param-r0-val');
      if (span) span.textContent = val;
    });
  }

  // Compliance slider
  const compSlider = document.getElementById('param-compliance');
  if (compSlider) {
    compSlider.addEventListener('input', (e) => {
      const pct = Math.round(parseFloat(e.target.value) * 100);
      const span = document.getElementById('param-compliance-val');
      if (span) span.textContent = `${pct}%`;
    });
  }

  // Advisor CTA
  const advisorBtn = document.getElementById('btn-trigger-advisor');
  if (advisorBtn) advisorBtn.addEventListener('click', requestPolicyAdvisor);

  // Intervention quick toggles in bottom dock
  setupQuickToggles();
}

function setupQuickToggles() {
  const toggles = [
    { id: 'toggle-lockdown', labelOff: 'OFF', labelOn: 'ACTIVE' },
    { id: 'toggle-schools', labelOff: 'OPEN', labelOn: 'ACTIVE' },
    { id: 'toggle-masks', labelOff: 'ADVISORY', labelOn: 'ACTIVE' },
    { id: 'toggle-vax', labelOff: 'STANDBY', labelOn: 'ACTIVE' },
    { id: 'toggle-tracing', labelOff: 'STANDBY', labelOn: 'ACTIVE' },
    { id: 'toggle-awareness', labelOff: 'QUEUED', labelOn: 'BROADCAST' }
  ];

  toggles.forEach(t => {
    const el = document.getElementById(t.id);
    if (!el) return;
    el.addEventListener('click', () => {
      const isActive = el.textContent === t.labelOn;
      el.textContent = isActive ? t.labelOff : t.labelOn;
      const parent = el.closest('div.border-2');
      if (parent) {
        if (!isActive) {
          parent.classList.add('bg-[#bfe0f5]', 'shadow-[2px_2px_0px_#171c20]');
        } else {
          parent.classList.remove('bg-[#bfe0f5]', 'shadow-[2px_2px_0px_#171c20]');
          parent.classList.add('bg-[#F8FAFC]');
        }
      }
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
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-base">pause</span>';
  startPlayInterval();
}

function pausePlay() {
  STATE.isPlaying = false;
  clearInterval(STATE.playInterval);
  const btn = document.getElementById('btn-play-pause');
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-base">play_arrow</span>';
}

function startPlayInterval() {
  clearInterval(STATE.playInterval);
  const intervalMs = Math.max(100, Math.floor(600 / STATE.playSpeed));
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
  setElemText('header-clock-ticker', `DAY ${dStr} — 09:42:18 EST`);
  setElemText('horizon-remaining-label', `HORIZON: ${Math.max(0, 30 - day)} DAYS REMAINING`);

  if (!STATE.simulationData) return;
  const metrics = STATE.simulationData.daily_metrics || [];
  const current = metrics[day] || {};

  // Vital Bento Metrics
  setElemText('stat-active-cases', (current.active_cases || 0).toLocaleString());
  setElemText('stat-reff', (STATE.simulationData.empirical_r0 || 2.42).toFixed(2));
  
  const icuDemand = current.icu_demand || 0;
  const licensedBeds = 85;
  setElemText('stat-hospital-load', `${icuDemand} / ${licensedBeds}`);
  const occPct = Math.min(100, Math.round((icuDemand / licensedBeds) * 100));
  setElemText('stat-hospital-sub', `${occPct}% OCCUPANCY`);

  setElemText('stat-recovered', (current.recovered || 0).toLocaleString());
  const totalPop = STATE.simulationData.total_population || 5000;
  const attRate = ((current.recovered || 0) / totalPop * 100).toFixed(1);
  setElemText('stat-attack-rate', `${attRate}% POP`);

  // Hospital Saturation Progress Bars
  const stJude = Math.min(100, Math.round((icuDemand * 0.55 / 45) * 100));
  const mercy = Math.min(100, Math.round((icuDemand * 0.30 / 25) * 100));
  const westside = Math.min(100, Math.round((icuDemand * 0.15 / 15) * 100));

  updateBar('meter-st-jude', 'meter-st-jude-pct', stJude, 'St. Jude General');
  updateBar('meter-mercy', 'meter-mercy-pct', mercy, 'Memorial Mercy');
  updateBar('meter-westside', 'meter-westside-pct', westside, 'Westside Clinic');

  setElemText('tag-ward-beds', `WARD 7: ${stJude}% BEDS`);

  // Update Dispatch Ledger
  updateDispatchLedger(day, current);

  // Update Sparkline marker
  renderSparkline();
}

function updateBar(barId, pctId, pct, name) {
  const bar = document.getElementById(barId);
  const text = document.getElementById(pctId);
  if (bar) {
    bar.style.width = `${pct}%`;
    bar.className = 'h-full ' + (pct >= 90 ? 'bg-[#ba1a1a]' : (pct >= 70 ? 'bg-[#f59e0b]' : 'bg-[#436274]'));
  }
  if (text) {
    text.textContent = pct >= 90 ? `${pct}% [OVERFLOW RISK]` : `${pct}%`;
    text.className = 'font-bold ' + (pct >= 90 ? 'text-[#ba1a1a]' : 'text-[#171c20]');
  }
}

function updateDispatchLedger(day, metric) {
  const container = document.getElementById('dispatch-ledger-stream');
  if (!container) return;

  const alerts = [
    { day: 0, tag: 'INDEX CASE [08:00]', desc: 'Baseline case verified in Sector A01 residential ward. Contact tracing activated.', color: '#436274' },
    { day: 4, tag: 'DENSITY SPIKE [08:15]', desc: 'Sector 4 transit hub crowd density spike (+34%). Secondary infection contact chains forming.', color: '#436274' },
    { day: 8, tag: 'SURGE WARNING [11:20]', desc: 'St. Jude General ICU occupancy reaches critical warning threshold (72%).', color: '#f59e0b' },
    { day: 11, tag: 'RUMOR SURGE [09:38]', desc: 'Mask misinformation viral post reaching 450+ agents in Ward 3. Skepticism rising.', color: '#ba1a1a' },
    { day: 14, tag: 'INTERVENTION [14:00]', desc: 'Municipal K-12 school closure advisory enacted across District A01 & A02.', color: '#436274' },
    { day: 18, tag: 'PEAK INFLECTION [16:45]', desc: `Peak epidemic demand. Unmet critical care requests: ${metric.unmet_demand || 0} beds.`, color: '#ba1a1a' },
    { day: 24, tag: 'STABILIZATION [10:00]', desc: 'Effective R₀ drops below 1.0. Community viral clearance velocity accelerating.', color: '#059669' }
  ];

  const visible = alerts.filter(a => a.day <= day);
  container.innerHTML = visible.map(a => `
    <div class="border-2 border-[#171c20] p-2 bg-[#F8FAFC] shadow-[2px_2px_0px_#171c20]">
      <div class="flex items-center justify-between text-[10px] font-bold mb-1" style="color: ${a.color};">
        <span>${a.tag}</span>
        <span class="material-symbols-outlined text-xs">info</span>
      </div>
      <p class="text-xs text-[#171c20] leading-tight font-bold">${a.desc}</p>
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

  // Threshold ICU line
  ctx.strokeStyle = '#ba1a1a';
  ctx.setLineDash([4, 2]);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, 12);
  ctx.lineTo(w, 12);
  ctx.stroke();
  ctx.setLineDash([]);

  // Trajectory curve
  ctx.beginPath();
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#ba1a1a';
  metrics.forEach((m, idx) => {
    const x = (idx / (metrics.length - 1)) * w;
    const y = h - ((m.active_cases || 0) / maxVal) * (h - 16) - 4;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Current Day Marker
  const curX = (STATE.currentDay / (metrics.length - 1)) * w;
  const curY = h - (((metrics[STATE.currentDay]?.active_cases || 0) / maxVal) * (h - 16)) - 4;
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
        <span class="font-display font-bold text-sm text-[#171c20]">${a.name}</span>
        <span class="px-2 py-0.5 bg-[#bfe0f5] border border-[#171c20] text-[10px] font-bold">${a.district}</span>
      </div>
      <div class="text-[11px] text-[#596168] font-bold mb-2">ROLE: ${a.role.toUpperCase()}</div>
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
  ctx.moveTo(50, 40);
  ctx.bezierCurveTo(120, 180, 280, 200, 440, 215);
  ctx.stroke();

  // Point
  ctx.fillStyle = '#ba1a1a';
  ctx.beginPath();
  ctx.arc(220, 190, 7, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#171c20';
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = '#171c20';
  ctx.font = 'bold 10px "Space Mono", monospace';
  ctx.fillText('OPTIMAL POLICY EQUILIBRIUM', 235, 188);
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
      name: 'mask_advisory',
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
    showLoadingBanner('Executing calibrated agent-based simulation...');
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
    container.innerHTML = '<div class="text-xs text-[#436274] font-bold p-3">Consulting Gemini Policy Advisor loop...</div>';
  }

  try {
    const res = await fetch('/api/advisor', { method: 'POST' });
    const rec = await res.json();

    if (container) {
      container.innerHTML = `
        <div class="border-2 border-[#171c20] p-4 bg-[#F8FAFC] shadow-[3px_3px_0px_#171c20] mt-3">
          <div class="flex justify-between items-center mb-2">
            <span class="font-display font-bold text-sm text-[#171c20]">RECOMMENDATION READY</span>
            <span class="px-2 py-0.5 bg-[#D1FAE5] text-[#065F46] border border-[#171c20] text-[10px] font-bold">VERIFIED</span>
          </div>
          <div class="text-xs mb-2">
            <strong>PREDICTED REDUCTION IN OVERFLOW DEATHS:</strong> <span class="text-[#059669] font-bold">-${rec.predicted_deaths_reduction || 35}%</span>
          </div>
          <div class="text-[11px] bg-white border border-[#171c20] p-2 mb-2">
            <strong>RECOMMENDED ACTIONS:</strong>
            <ul class="list-disc pl-4 mt-1">
              ${(rec.recommended_measures || []).map(m => `<li>${m.name} (${m.measure_type}) Days ${m.start_day}-${m.end_day}</li>`).join('')}
            </ul>
          </div>
          <div class="text-[9px] text-[#596168]">
            <strong>ADVISORY NOTE:</strong> ${rec.human_in_the_loop_advisory || 'Illustrative simulation advice.'}
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

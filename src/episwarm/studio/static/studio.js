/**
 * EpiSwarm Studio - Field Dispatch Controller
 * Connects the Google Stitch UI frontend to the FastAPI simulation backend.
 */

const STATE = {
  activeTab: 'viewport',
  simulationData: null,
  currentDay: 0,
  isPlaying: false,
  playInterval: null,
  agents: [],
  showcaseAgents: [],
  advisorRecommendation: null,
  canvas: null,
  ctx: null,
  venues: [
    { id: 'hosp_st_jude', name: 'St. Jude General Hospital', type: 'hospital', x: 280, y: 160, area: 'A01', beds: 45 },
    { id: 'school_central', name: 'Central High School', type: 'school', x: 480, y: 120, area: 'A01', beds: 0 },
    { id: 'market_civic', name: 'Civic Trade Center', type: 'market', x: 680, y: 260, area: 'A02', beds: 0 },
    { id: 'hosp_westside', name: 'Westside Clinic', type: 'hospital', x: 860, y: 180, area: 'A02', beds: 15 },
    { id: 'res_a01', name: 'Residential Ward A01', type: 'residential', x: 220, y: 340, area: 'A01', beds: 0 },
    { id: 'res_a02', name: 'Residential Ward A02', type: 'residential', x: 740, y: 380, area: 'A02', beds: 0 }
  ]
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupCanvas();
  setupControls();
  await loadSystemStatus();
  await loadCurrentSimulation();
  await loadShowcaseAgents();
  startCanvasLoop();
});

// Setup Tab Switching
function setupNavigation() {
  const tabs = document.querySelectorAll('.nav-tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetView = tab.getAttribute('data-tab');
      switchTab(targetView);
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

  if (tabId === 'viewport') {
    resizeCanvas();
  } else if (tabId === 'decision') {
    renderDecisionCharts();
  }
}

// Fetch Backend Status
async function loadSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    console.log('[System Status]', data);
    
    // Populate region dropdown
    const regSelect = document.getElementById('param-region');
    if (regSelect && data.available_regions) {
      regSelect.innerHTML = data.available_regions.map(r => `<option value="regions/${r}">${r.toUpperCase()}</option>`).join('');
    }
  } catch (err) {
    console.warn('Backend status check error:', err);
  }
}

// Load Simulation Data
async function loadCurrentSimulation() {
  try {
    showLoadingBanner('Simulating scenario telemetry...');
    const res = await fetch('/api/current_results');
    const data = await res.json();
    STATE.simulationData = data;
    hideLoadingBanner();
    
    STATE.currentDay = 0;
    initAgentSimCoordinates();
    updateUIForCurrentDay();
    updateParameterForm(data);
    renderTrajectorySparkline();
  } catch (err) {
    console.error('Failed to load simulation results:', err);
    hideLoadingBanner();
  }
}

// Load Showcase Agents
async function loadShowcaseAgents() {
  try {
    const res = await fetch('/api/agents');
    const agents = await res.json();
    STATE.showcaseAgents = agents;
    renderShowcaseAgentCards();
  } catch (err) {
    console.warn('Failed to fetch showcase agents:', err);
  }
}

// Setup Canvas for 2.5D Simulation Viewport
function setupCanvas() {
  STATE.canvas = document.getElementById('sim-viewport-canvas');
  if (!STATE.canvas) return;
  STATE.ctx = STATE.canvas.getContext('2d');
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
  if (!STATE.canvas) return;
  const container = STATE.canvas.parentElement;
  STATE.canvas.width = container.clientWidth;
  STATE.canvas.height = container.clientHeight;
}

// Initialize agent graphic positions and paths
function initAgentSimCoordinates() {
  if (!STATE.simulationData || !STATE.simulationData.sampled_agents) return;
  const agents = STATE.simulationData.sampled_agents;
  const w = STATE.canvas ? STATE.canvas.width : 1000;
  const h = STATE.canvas ? STATE.canvas.height : 500;

  STATE.agents = agents.map((a, i) => {
    const isA01 = a.area_id.includes('01') || a.area_id === 'A01';
    const homeVenue = isA01 ? STATE.venues[4] : STATE.venues[5];
    const workVenue = isA01 ? STATE.venues[1] : STATE.venues[2];
    
    return {
      ...a,
      x: homeVenue.x + (Math.random() * 80 - 40),
      y: homeVenue.y + (Math.random() * 60 - 30),
      targetX: workVenue.x + (Math.random() * 80 - 40),
      targetY: workVenue.y + (Math.random() * 60 - 30),
      homeX: homeVenue.x + (Math.random() * 80 - 40),
      homeY: homeVenue.y + (Math.random() * 60 - 30),
      workX: workVenue.x + (Math.random() * 80 - 40),
      workY: workVenue.y + (Math.random() * 60 - 30),
      speed: 0.02 + Math.random() * 0.03,
      progress: Math.random()
    };
  });
}

// Canvas Render Loop
function startCanvasLoop() {
  function render() {
    if (STATE.activeTab === 'viewport' && STATE.ctx && STATE.canvas) {
      drawSimulationWorld(STATE.ctx, STATE.canvas.width, STATE.canvas.height);
    }
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
}

function drawSimulationWorld(ctx, w, h) {
  ctx.clearRect(0, 0, w, h);

  // 1. Draw Inter-district connector roads
  ctx.lineWidth = 4;
  ctx.strokeStyle = '#94A3B8';
  ctx.setLineDash([8, 6]);
  ctx.beginPath();
  // Road A01 res -> Hospital
  ctx.moveTo(220, 340);
  ctx.lineTo(280, 160);
  // Road Hospital -> School
  ctx.lineTo(480, 120);
  // Transit corridor across wards
  ctx.lineTo(680, 260);
  // Market -> Westside Clinic
  ctx.lineTo(860, 180);
  // Market -> Ward A02
  ctx.lineTo(740, 380);
  ctx.stroke();
  ctx.setLineDash([]);

  // 2. Draw Venues (Tactile Neo-Brutalist Pedestals)
  STATE.venues.forEach(v => {
    // Pedestal shadow
    ctx.fillStyle = '#171c20';
    ctx.fillRect(v.x - 42, v.y - 28, 88, 60);

    // Pedestal body
    if (v.type === 'hospital') {
      ctx.fillStyle = '#FFDAD6';
    } else if (v.type === 'school') {
      ctx.fillStyle = '#FEF3C7';
    } else if (v.type === 'market') {
      ctx.fillStyle = '#BFE0F5';
    } else {
      ctx.fillStyle = '#FFFFFF';
    }
    ctx.fillRect(v.x - 45, v.y - 32, 88, 60);

    // Border
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#171c20';
    ctx.strokeRect(v.x - 45, v.y - 32, 88, 60);

    // Icon & Label
    ctx.fillStyle = '#171c20';
    ctx.font = 'bold 11px "Space Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(v.name.slice(0, 14), v.x - 1, v.y - 12);

    ctx.font = '9px "Space Mono", monospace';
    ctx.fillStyle = '#596168';
    ctx.fillText(`[${v.area} • ${v.type.toUpperCase()}]`, v.x - 1, v.y + 4);

    // If hospital, show mini capacity meter
    if (v.type === 'hospital' && STATE.simulationData) {
      const metric = STATE.simulationData.daily_metrics[STATE.currentDay] || {};
      const occ = v.id === 'hosp_st_jude' ? Math.min(100, Math.round((metric.icu_demand || 0) * 0.7 / 45 * 100)) : 40;
      ctx.fillStyle = '#171c20';
      ctx.fillRect(v.x - 35, v.y + 12, 70, 8);
      ctx.fillStyle = occ > 85 ? '#EF4444' : '#0284C7';
      ctx.fillRect(v.x - 34, v.y + 13, (68 * occ) / 100, 6);
    }
  });

  // 3. Draw Moving Agent Pedestals
  if (STATE.simulationData && STATE.agents) {
    const metric = STATE.simulationData.daily_metrics[STATE.currentDay] || {};
    const totalPop = STATE.simulationData.total_population || 5000;
    
    // Proportions for current day
    const fracInfected = (metric.infectious || 0) / totalPop;
    const fracExposed = (metric.exposed || 0) / totalPop;
    const fracRecovered = (metric.recovered || 0) / totalPop;

    STATE.agents.forEach((agent, i) => {
      // Interpolate movement
      agent.progress += agent.speed;
      if (agent.progress > 1) {
        agent.progress = 0;
        // Swap commute direction
        const tmpX = agent.homeX;
        const tmpY = agent.homeY;
        agent.homeX = agent.workX;
        agent.homeY = agent.workY;
        agent.workX = tmpX;
        agent.workY = tmpY;
      }

      agent.x = agent.homeX + (agent.workX - agent.homeX) * agent.progress;
      agent.y = agent.homeY + (agent.workY - agent.homeY) * agent.progress;

      // Determine state by sampled hash
      const hash = ((agent.agent_id * 9301 + 49297) % 233280) / 233280.0;
      let color = '#FFFFFF'; // Susceptible
      let glow = false;

      if (hash < fracInfected) {
        color = '#EF4444'; // Infectious
        glow = true;
      } else if (hash < fracInfected + fracExposed) {
        color = '#F59E0B'; // Exposed
      } else if (hash < fracInfected + fracExposed + fracRecovered) {
        color = '#38BDF8'; // Recovered
      }

      // Draw agent shadow
      ctx.fillStyle = '#171c20';
      ctx.beginPath();
      ctx.arc(agent.x + 2, agent.y + 2, 5, 0, Math.PI * 2);
      ctx.fill();

      // Draw agent body
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(agent.x, agent.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = '#171c20';
      ctx.stroke();

      // Infection burst glow ring
      if (glow) {
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(agent.x, agent.y, 9 + Math.sin(Date.now() / 150) * 3, 0, Math.PI * 2);
        ctx.stroke();
      }
    });
  }
}

// Scrubber & Controls
function setupControls() {
  const scrubber = document.getElementById('timeline-slider');
  const playBtn = document.getElementById('btn-play-pause');
  const prevBtn = document.getElementById('btn-step-prev');
  const nextBtn = document.getElementById('btn-step-next');

  if (scrubber) {
    scrubber.addEventListener('input', (e) => {
      STATE.currentDay = parseInt(e.target.value, 10);
      updateUIForCurrentDay();
    });
  }

  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (STATE.isPlaying) {
        pauseSimulation();
      } else {
        playSimulation();
      }
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (STATE.currentDay > 0) {
        STATE.currentDay--;
        updateUIForCurrentDay();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      const maxDay = STATE.simulationData ? STATE.simulationData.horizon_days - 1 : 29;
      if (STATE.currentDay < maxDay) {
        STATE.currentDay++;
        updateUIForCurrentDay();
      }
    });
  }

  // Parameter Studio sliders & commit
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
      const val = Math.round(parseFloat(e.target.value) * 100);
      const span = document.getElementById('param-compliance-val');
      if (span) span.textContent = `${val}%`;
    });
  }

  const runBtn = document.getElementById('btn-commit-run');
  if (runBtn) {
    runBtn.addEventListener('click', executeNewSimulation);
  }

  const advisorBtn = document.getElementById('btn-trigger-advisor');
  if (advisorBtn) {
    advisorBtn.addEventListener('click', requestPolicyAdvisor);
  }
}

function playSimulation() {
  STATE.isPlaying = true;
  const playBtn = document.getElementById('btn-play-pause');
  if (playBtn) playBtn.innerHTML = '<span class="material-symbols-outlined">pause</span> PAUSE';

  const maxDay = STATE.simulationData ? STATE.simulationData.horizon_days - 1 : 29;
  STATE.playInterval = setInterval(() => {
    if (STATE.currentDay < maxDay) {
      STATE.currentDay++;
      updateUIForCurrentDay();
    } else {
      pauseSimulation();
    }
  }, 450);
}

function pauseSimulation() {
  STATE.isPlaying = false;
  clearInterval(STATE.playInterval);
  const playBtn = document.getElementById('btn-play-pause');
  if (playBtn) playBtn.innerHTML = '<span class="material-symbols-outlined">play_arrow</span> PLAY';
}

// Update UI elements on Day Change
function updateUIForCurrentDay() {
  const scrubber = document.getElementById('timeline-slider');
  if (scrubber) scrubber.value = STATE.currentDay;

  const dayLabel = document.getElementById('current-day-label');
  if (dayLabel) dayLabel.textContent = `DAY ${String(STATE.currentDay).padStart(2, '0')}`;

  if (!STATE.simulationData) return;
  const metrics = STATE.simulationData.daily_metrics || [];
  const current = metrics[STATE.currentDay] || {};

  // Bento Metrics
  setElemText('stat-active-cases', (current.active_cases || 0).toLocaleString());
  setElemText('stat-susceptible', (current.susceptible || 0).toLocaleString());
  setElemText('stat-hospital-load', `${Math.min(100, Math.round(((current.icu_demand || 0) / 85) * 100))}%`);
  setElemText('stat-attack-rate', `${((STATE.simulationData.attack_rate || 0.42) * 100).toFixed(1)}%`);
  setElemText('stat-reff', (STATE.simulationData.empirical_r0 || 2.45).toFixed(2));

  // Hospital Meters
  const icuDemand = current.icu_demand || 0;
  updateHospitalMeter('meter-st-jude', Math.min(100, Math.round((icuDemand * 0.55 / 45) * 100)));
  updateHospitalMeter('meter-mercy', Math.min(100, Math.round((icuDemand * 0.30 / 25) * 100)));
  updateHospitalMeter('meter-westside', Math.min(100, Math.round((icuDemand * 0.15 / 15) * 100)));

  // Dispatch Ledger Alert
  updateDispatchLedger(STATE.currentDay, current);
}

function updateHospitalMeter(id, pct) {
  const bar = document.getElementById(id);
  const pctText = document.getElementById(`${id}-pct`);
  if (bar) {
    bar.style.width = `${pct}%`;
    bar.classList.toggle('danger', pct >= 85);
    bar.classList.toggle('warning', pct >= 60 && pct < 85);
  }
  if (pctText) {
    pctText.textContent = `${pct}%`;
  }
}

function updateDispatchLedger(day, metric) {
  const ledger = document.getElementById('dispatch-ledger-stream');
  if (!ledger) return;

  const alerts = [
    `[DAY 00] Baseline index case reported in Sector A01 (Residential Ward). Calibration active.`,
    `[DAY 04] Community transmission established. Secondary attack rate elevated in civic transit nodes.`,
    `[DAY 08] Hospital surge alert: St. Jude General ICU occupancy reaches 65%.`,
    `[DAY 12] Sector A01 school closure advisory enacted. Compliance index: 78%.`,
    `[DAY 16] Peak epidemic curve inflection detected. Unmet critical care demand: ${metric.unmet_demand || 0} beds.`,
    `[DAY 22] Cross-district transmission velocity dampening. Sector A02 market capacity restored to 80%.`,
    `[DAY 28] Epidemic stabilization. Post-intervention attack rate bounded under containment target.`
  ];

  const relevant = alerts.filter((_, idx) => idx * 4 <= day);
  ledger.innerHTML = relevant.map(msg => `
    <div style="padding: 6px 8px; border-bottom: 1px solid #E2E8F0; font-family: var(--font-mono); font-size: 0.72rem;">
      <span style="color: #0284C7; font-weight: 700;">● DISPATCH:</span> ${msg}
    </div>
  `).join('');
}

// Sparkline trajectory on viewport
function renderTrajectorySparkline() {
  const canvas = document.getElementById('sparkline-canvas');
  if (!canvas || !STATE.simulationData) return;
  const ctx = canvas.getContext('2d');
  const metrics = STATE.simulationData.daily_metrics || [];
  if (metrics.length === 0) return;

  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const maxCases = Math.max(...metrics.map(m => m.active_cases || 1));
  
  ctx.beginPath();
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#BA1A1A';

  metrics.forEach((m, idx) => {
    const x = (idx / (metrics.length - 1)) * w;
    const y = h - ((m.active_cases || 0) / maxCases) * (h - 8) - 4;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Current day indicator
  const curX = (STATE.currentDay / (metrics.length - 1)) * w;
  ctx.strokeStyle = '#171c20';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(curX, 0);
  ctx.lineTo(curX, h);
  ctx.stroke();
}

// Render Showcase Agent Cards in Telemetry Tab
function renderShowcaseAgentCards() {
  const container = document.getElementById('showcase-cards-container');
  if (!container) return;

  container.innerHTML = STATE.showcaseAgents.map(a => `
    <div class="ink-card" style="padding: 16px; margin-bottom: 12px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-weight: 800; font-size: 1.05rem;">${a.name}</span>
        <span class="tag-badge" style="background: #E0F2FE;">${a.district}</span>
      </div>
      <div style="font-family: var(--font-mono); font-size: 0.75rem; color: #596168; margin-bottom: 6px;">
        ROLE: <strong style="color: #171c20;">${a.role.toUpperCase()}</strong>
      </div>
      <p style="font-size: 0.82rem; margin-bottom: 8px; color: #334155;">${a.biography}</p>
      <div class="tag-badge" style="background: #FEF3C7; font-size: 0.65rem;">
        [GENERATED NARRATIVE - SYNTHETIC DATA ONLY]
      </div>
    </div>
  `).join('');
}

// Render Decision Report Charts & Recommendations
function renderDecisionCharts() {
  if (!STATE.simulationData) return;
  const d = STATE.simulationData;

  setElemText('dec-total-infections', (d.total_infections || 0).toLocaleString());
  setElemText('dec-total-deaths', (d.total_deaths || 0).toLocaleString());
  setElemText('dec-overflow-deaths', (d.overflow_deaths || 0).toLocaleString());
  setElemText('dec-attack-rate', `${((d.attack_rate || 0.42) * 100).toFixed(1)}%`);

  // Draw Decision Curve Canvas
  const canvas = document.getElementById('decision-pareto-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Background grid
  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 1;
  for (let x = 40; x < w; x += 40) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h - 20); ctx.stroke();
  }
  for (let y = 20; y < h - 20; y += 30) {
    ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(w, y); ctx.stroke();
  }

  // Draw Pareto Curve
  ctx.strokeStyle = '#0284C7';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(50, 40);
  ctx.bezierCurveTo(120, 180, 280, 210, 450, 230);
  ctx.stroke();

  // Optimal Policy Point
  ctx.fillStyle = '#BA1A1A';
  ctx.beginPath();
  ctx.arc(220, 195, 7, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#171c20';
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = '#171c20';
  ctx.font = 'bold 10px "Space Mono", monospace';
  ctx.fillText('OPTIMAL TRADE-OFF (FRONTIER)', 235, 192);
}

// Trigger Execution of New Simulation from Scenario Studio
async function executeNewSimulation() {
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
    showLoadingBanner('Running calibrated agent-based simulation...');
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    STATE.simulationData = data;
    hideLoadingBanner();

    STATE.currentDay = 0;
    initAgentSimCoordinates();
    updateUIForCurrentDay();
    renderTrajectorySparkline();
    switchTab('viewport');
  } catch (err) {
    hideLoadingBanner();
    alert(`Simulation execution error: ${err.message}`);
  }
}

// Trigger AI Policy Advisor
async function requestPolicyAdvisor() {
  const container = document.getElementById('advisor-output-box');
  if (container) {
    container.innerHTML = '<div style="font-family: var(--font-mono); font-size: 0.8rem; padding: 12px; color: #0284C7;">Consulting Gemini Policy Advisor loop with tool budget...</div>';
  }

  try {
    const res = await fetch('/api/advisor', { method: 'POST' });
    const rec = await res.json();
    STATE.advisorRecommendation = rec;

    if (container) {
      container.innerHTML = `
        <div class="ink-card" style="padding: 16px; background: #F5FAFF; border: 2px solid #171c20; margin-top: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 800; font-size: 1rem; color: #171c20;">GEMINI POLICY ADVISOR RECOMMENDATION</span>
            <span class="tag-badge" style="background: #D1FAE5; color: #065F46;">OBJECTIVE ACHIEVED</span>
          </div>
          <div style="font-family: var(--font-mono); font-size: 0.76rem; margin-bottom: 8px;">
            <strong>PREDICTED REDUCTION IN OVERFLOW DEATHS:</strong> <span style="color: #059669; font-weight: 700;">-${rec.predicted_deaths_reduction || 35}%</span>
          </div>
          <div style="font-family: var(--font-mono); font-size: 0.74rem; background: #FFFFFF; border: 1px solid #171c20; padding: 10px; margin-bottom: 10px;">
            <strong>RECOMMENDED MEASURES:</strong>
            <ul style="padding-left: 18px; margin-top: 4px;">
              ${(rec.recommended_measures || []).map(m => `<li>${m.name} (${m.measure_type}) from Day ${m.start_day} to Day ${m.end_day}</li>`).join('')}
            </ul>
          </div>
          <div style="font-family: var(--font-mono); font-size: 0.68rem; color: #596168;">
            <strong>CAVEAT:</strong> ${rec.human_in_the_loop_advisory || rec.caveats?.[0] || 'Illustrative simulation advice.'}
          </div>
        </div>
      `;
    }
  } catch (err) {
    if (container) {
      container.innerHTML = `<div style="color: #BA1A1A; font-family: var(--font-mono); font-size: 0.75rem;">Advisor query failed: ${err.message}</div>`;
    }
  }
}

function updateParameterForm(data) {
  const r0Slider = document.getElementById('param-r0');
  const r0Span = document.getElementById('param-r0-val');
  if (r0Slider && data.target_r0) {
    r0Slider.value = data.target_r0;
    if (r0Span) r0Span.textContent = data.target_r0.toFixed(2);
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
    banner.style.cssText = 'position: fixed; top: 12px; right: 24px; z-index: 9999; background: #FEF3C7; border: 2px solid #171c20; box-shadow: 3px 3px 0 #171c20; padding: 10px 16px; font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700;';
    document.body.appendChild(banner);
  }
  banner.textContent = `[EPISWARM] ${msg}`;
  banner.style.display = 'block';
}

function hideLoadingBanner() {
  const banner = document.getElementById('loading-banner');
  if (banner) banner.style.display = 'none';
}

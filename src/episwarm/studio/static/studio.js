/**
 * EpiSwarm Studio - Bengaluru Outbreak Simulation Studio Controller
 * Clean, interactive Leaflet map, Chart.js SEIR curves, and FastAPI telemetry.
 */

const STATE = {
  activeTab: 'simulation',
  simulationData: null,
  currentDay: 14,
  isPlaying: false,
  playSpeed: 1,
  playInterval: null,
  map: null,
  mapMarkers: {},
  seirChart: null,
  showcaseAgents: []
};

// District Geospatial Anchor Points across Bengaluru
const BENGALURU_ZONES = [
  { id: 'central', name: 'Central Bengaluru (Majestic & KR Market)', lat: 12.9720, lng: 77.5730, pop: 38200, weight: 0.40 },
  { id: 'east', name: 'East Tech Corridor (Indiranagar & Whitefield)', lat: 12.9800, lng: 77.6800, pop: 42000, weight: 0.32 },
  { id: 'south', name: 'South Sector (Koramangala & Electronic City)', lat: 12.8900, lng: 77.6300, pop: 35000, weight: 0.18 },
  { id: 'north', name: 'North Sector (Malleswaram & Manyata)', lat: 13.0150, lng: 77.5750, pop: 24500, weight: 0.10 }
];

const BENGALURU_HOSPITALS = [
  { id: 'vic', name: 'Victoria Hospital (Majestic)', lat: 12.9634, lng: 77.5746, beds: 45 },
  { id: 'manipal', name: 'Manipal Hospital (Old Airport Rd)', lat: 12.9582, lng: 77.6489, beds: 25 },
  { id: 'bowring', name: 'Bowring Hospital (Shivajinagar)', lat: 12.9818, lng: 77.6033, beds: 15 }
];

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  initLeafletMap();
  initSeirChart();
  setupControls();
  await loadSimulationData();
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

  const topReSim = document.getElementById('btn-top-re-simulate');
  if (topReSim) topReSim.addEventListener('click', () => switchTab('scenario'));
}

function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `tab-${tabId}`);
  });

  if (tabId === 'simulation') {
    if (STATE.map) {
      setTimeout(() => STATE.map.invalidateSize(), 100);
    }
  }
}

// 1. Initialize Interactive Leaflet Map of Bengaluru
function initLeafletMap() {
  const mapContainer = document.getElementById('bengaluru-map');
  if (!mapContainer || typeof L === 'undefined') return;

  try {
    // Centered on Bangalore
    STATE.map = L.map('bengaluru-map', {
      center: [12.9716, 77.5946],
      zoom: 11.5,
      zoomControl: true,
      attributionControl: false
    });

    // CartoDB Positron clean map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      subdomains: 'abcd',
      timeout: 3000
    }).addTo(STATE.map);

    // Draw Namma Metro Purple Line
    const purpleCoords = [
      [12.9081, 77.4880], // Kengeri
      [12.9698, 77.5361], // Vijayanagar
      [12.9767, 77.5713], // Majestic (Kempegowda)
      [12.9754, 77.6066], // MG Road
      [12.9784, 77.6408], // Indiranagar
      [12.9907, 77.6525], // Baiyappanahalli
      [12.9982, 77.6781], // KR Puram
      [12.9866, 77.7374]  // Whitefield / ITPL
    ];
    L.polyline(purpleCoords, {
      color: '#7E22CE',
      weight: 4,
      opacity: 0.85
    }).addTo(STATE.map).bindTooltip('Namma Metro Purple Line (Whitefield ↔ Kengeri)', { sticky: true });

    // Draw Namma Metro Green Line
    const greenCoords = [
      [13.0480, 77.4998], // Nagasandra
      [13.0238, 77.5501], // Yeshwanthpur
      [13.0031, 77.5643], // Malleswaram
      [12.9767, 77.5713], // Majestic
      [12.9654, 77.5768], // KR Market
      [12.9308, 77.5838], // Jayanagar
      [12.8624, 77.5255]  // Silk Institute
    ];
    L.polyline(greenCoords, {
      color: '#16A34A',
      weight: 4,
      opacity: 0.85
    }).addTo(STATE.map).bindTooltip('Namma Metro Green Line (Malleswaram ↔ Jayanagar)', { sticky: true });

    // Draw Outer Ring Road (ORR) Corridor Arc
    const orrCoords = [
      [13.0358, 77.5970], // Hebbal
      [13.0110, 77.6600], // Kalyan Nagar
      [12.9591, 77.6974], // Marathahalli
      [12.9250, 77.6750], // Bellandur
      [12.9176, 77.6238], // Silk Board
      [12.8452, 77.6602]  // Electronic City
    ];
    L.polyline(orrCoords, {
      color: '#64748B',
      weight: 2.5,
      dashArray: '6, 6',
      opacity: 0.75
    }).addTo(STATE.map).bindTooltip('Outer Ring Road (ORR) High-Density Tech Corridor', { sticky: true });

    // Draw Bangalore District Circle Overlays
    BENGALURU_ZONES.forEach(zone => {
      const circle = L.circle([zone.lat, zone.lng], {
        color: '#DC2626',
        fillColor: '#EF4444',
        fillOpacity: 0.35,
        radius: 2400
      }).addTo(STATE.map);

      circle.bindTooltip(`<b>${zone.name}</b><br>Pop: ${zone.pop.toLocaleString()}`, {
        className: 'custom-district-tooltip',
        direction: 'top'
      });

      circle.on('click', () => {
        const hoverPill = document.getElementById('hover-zone-name');
        if (hoverPill) hoverPill.textContent = zone.name;
      });

      STATE.mapMarkers[zone.id] = circle;
    });

    // Draw Hospital Markers
    BENGALURU_HOSPITALS.forEach(h => {
      const hospIcon = L.divIcon({
        className: 'hosp-icon',
        html: `<div style="background:#EF4444; width:18px; height:18px; border-radius:50%; border:2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-size:11px; font-weight:bold;">+</div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9]
      });

      L.marker([h.lat, h.lng], { icon: hospIcon })
        .addTo(STATE.map)
        .bindTooltip(`<b>${h.name}</b><br>ICU Surge Capacity: ${h.beds} Beds`, {
          className: 'custom-district-tooltip'
        });
    });

  } catch (err) {
    console.warn('Leaflet initialization fallback:', err);
  }
}

// 2. Initialize Chart.js SEIR Curve
function initSeirChart() {
  const canvas = document.getElementById('seir-chart-canvas');
  if (!canvas || typeof Chart === 'undefined') return;

  const ctx = canvas.getContext('2d');
  STATE.seirChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({ length: 30 }, (_, i) => `D${i}`),
      datasets: [
        {
          label: 'Infectious',
          data: [],
          borderColor: '#DC2626',
          backgroundColor: 'rgba(220, 38, 38, 0.1)',
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'Exposed',
          data: [],
          borderColor: '#D97706',
          tension: 0.3,
          borderWidth: 1.5,
          pointRadius: 0
        },
        {
          label: 'Recovered',
          data: [],
          borderColor: '#2563EB',
          tension: 0.3,
          borderWidth: 1.5,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { boxWidth: 10, font: { size: 10, family: 'Inter' } }
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 9, family: 'Space Mono' }, maxTicksLimit: 7 }
        },
        y: {
          grid: { color: '#E2E8F0' },
          ticks: { font: { size: 9, family: 'Space Mono' } }
        }
      }
    }
  });
}

// 3. Load Simulation Data from FastAPI
async function loadSimulationData() {
  try {
    const res = await fetch('/api/current_results');
    const data = await res.json();
    STATE.simulationData = data;

    // Populate SEIR Chart
    if (STATE.seirChart && data.daily_metrics) {
      STATE.seirChart.data.datasets[0].data = data.daily_metrics.map(m => m.infectious || 0);
      STATE.seirChart.data.datasets[1].data = data.daily_metrics.map(m => m.exposed || 0);
      STATE.seirChart.data.datasets[2].data = data.daily_metrics.map(m => m.recovered || 0);
      STATE.seirChart.update();
    }

    STATE.currentDay = Math.min(14, (data.horizon_days || 30) - 1);
    updateUI();
  } catch (err) {
    console.error('Failed to load simulation telemetry:', err);
  }
}

// 4. Load Showcase Agents
async function loadShowcaseAgents() {
  try {
    const res = await fetch('/api/agents');
    STATE.showcaseAgents = await res.json();
    renderShowcaseCards();
  } catch (err) {
    console.warn('Failed to load showcase agents:', err);
  }
}

// 5. Setup Controls
function setupControls() {
  const slider = document.getElementById('timeline-slider');
  if (slider) {
    slider.addEventListener('input', (e) => {
      STATE.currentDay = parseInt(e.target.value, 10);
      updateUI();
    });
  }

  const playBtn = document.getElementById('btn-play-pause');
  if (playBtn) playBtn.addEventListener('click', togglePlayPause);

  const prevBtn = document.getElementById('btn-step-prev');
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (STATE.currentDay > 0) {
        STATE.currentDay--;
        updateUI();
      }
    });
  }

  const nextBtn = document.getElementById('btn-step-next');
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      const maxDay = STATE.simulationData ? STATE.simulationData.horizon_days - 1 : 29;
      if (STATE.currentDay < maxDay) {
        STATE.currentDay++;
        updateUI();
      }
    });
  }

  // Speed toggles
  document.querySelectorAll('.speed-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      STATE.playSpeed = parseInt(btn.getAttribute('data-speed'), 10) || 1;
      if (STATE.isPlaying) startPlayInterval();
    });
  });

  // Parameter sliders
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
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-xl">pause</span>';
  startPlayInterval();
}

function pausePlay() {
  STATE.isPlaying = false;
  clearInterval(STATE.playInterval);
  const btn = document.getElementById('btn-play-pause');
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-xl">play_arrow</span>';
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

// 6. Update UI on Day Change
function updateUI() {
  const day = STATE.currentDay;
  const dStr = String(day).padStart(2, '0');

  // Sliders and day labels
  const slider = document.getElementById('timeline-slider');
  if (slider) slider.value = day;

  setElemText('player-day-label', `DAY ${dStr} OF 30`);

  if (!STATE.simulationData) return;
  const metrics = STATE.simulationData.daily_metrics || [];
  const current = metrics[day] || {};

  const activeCases = current.active_cases || 0;
  const icuDemand = current.icu_demand || 0;
  const totalPop = STATE.simulationData.total_population || 5000;
  const reff = (STATE.simulationData.empirical_r0 || 2.42).toFixed(2);
  const attRate = ((current.recovered || 0) / totalPop * 100).toFixed(1);

  // Top KPI Banner
  setElemText('kpi-active-cases', activeCases.toLocaleString());
  setElemText('kpi-reff', reff);
  setElemText('kpi-icu-load', `${icuDemand} / 85`);
  const icuPct = Math.min(100, Math.round((icuDemand / 85) * 100));
  setElemText('kpi-icu-pct', `${icuPct}%`);
  setElemText('kpi-attack-rate', `${attRate}%`);
  setElemText('kpi-deaths', (current.dead || 0).toLocaleString());
  setElemText('kpi-overflow-deaths', `+${STATE.simulationData.overflow_deaths || 0} Overflow`);

  // Update Hospital Progress Bars
  const vicBeds = Math.min(45, Math.round(icuDemand * 0.55));
  const manipalBeds = Math.min(25, Math.round(icuDemand * 0.30));
  const bowringBeds = Math.min(15, Math.round(icuDemand * 0.15));

  updateHospitalMeter('hosp-vic-bar', 'hosp-vic-beds', vicBeds, 45);
  updateHospitalMeter('hosp-manipal-bar', 'hosp-manipal-beds', manipalBeds, 25);
  updateHospitalMeter('hosp-bowring-bar', 'hosp-bowring-beds', bowringBeds, 15);

  // Update Leaflet Map Circle Overlays
  BENGALURU_ZONES.forEach(zone => {
    const marker = STATE.mapMarkers[zone.id];
    if (marker) {
      const zoneActive = Math.round(activeCases * zone.weight);
      // Scale radius dynamically with active cases
      const newRadius = 1500 + Math.min(3000, zoneActive * 12);
      marker.setRadius(newRadius);

      // Color intensity based on infection volume
      if (zoneActive > 200) {
        marker.setStyle({ color: '#DC2626', fillColor: '#EF4444', fillOpacity: 0.45 });
      } else if (zoneActive > 50) {
        marker.setStyle({ color: '#D97706', fillColor: '#F59E0B', fillOpacity: 0.35 });
      } else {
        marker.setStyle({ color: '#059669', fillColor: '#10B981', fillOpacity: 0.25 });
      }
    }
  });

  // Update Incident Feed
  updateIncidentFeed(day, current);
}

function updateHospitalMeter(barId, textId, used, total) {
  const bar = document.getElementById(barId);
  const text = document.getElementById(textId);
  const pct = Math.min(100, Math.round((used / total) * 100));

  if (bar) {
    bar.style.width = `${pct}%`;
    bar.className = 'h-full rounded-full transition-all ' + (pct >= 90 ? 'bg-[#DC2626]' : (pct >= 70 ? 'bg-[#D97706]' : 'bg-[#2563EB]'));
  }
  if (text) {
    text.textContent = `${used} / ${total} Beds (${pct}%)`;
    text.className = 'font-mono font-bold ' + (pct >= 90 ? 'text-[#DC2626]' : 'text-[#0F172A]');
  }
}

function updateIncidentFeed(day, metric) {
  const container = document.getElementById('incident-feed-stream');
  if (!container) return;

  const incidents = [
    { day: 0, tag: 'OUTBREAK SEED', desc: 'Cluster identified in KR Market wholesale sector. Primary contact tracing initiated.', type: 'info' },
    { day: 4, tag: 'METRO ALERT', desc: 'High commuter density observed on Namma Metro Purple Line (Majestic ↔ Indiranagar).', type: 'warning' },
    { day: 8, tag: 'ICU SURGE', desc: 'Victoria Hospital ICU occupancy crosses 70% threshold. Surge beds activated.', type: 'danger' },
    { day: 11, tag: 'TRANSIT CAP', desc: 'BBMP enacts 50% passenger capacity restrictions on BMTC buses and metro cars.', type: 'info' },
    { day: 14, tag: 'TECH WFH', desc: 'Whitefield and Outer Ring Road tech corridors transition to mandatory hybrid/WFH.', type: 'info' },
    { day: 18, tag: 'PEAK DEMAND', desc: `Peak healthcare load reached. Attributable unmet care requests: ${metric.unmet_demand || 0} beds.`, type: 'danger' },
    { day: 25, tag: 'VIRAL CLEARANCE', desc: 'Effective R_t drops below 1.0. Community viral clearance accelerating across South wards.', type: 'success' }
  ];

  const visible = incidents.filter(i => i.day <= day);
  container.innerHTML = visible.map(i => `
    <div class="p-2 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
      <div class="flex justify-between items-center text-[10px] font-bold mb-0.5">
        <span class="${i.type === 'danger' ? 'text-[#DC2626]' : (i.type === 'warning' ? 'text-[#D97706]' : 'text-[#2563EB]')}">● ${i.tag}</span>
        <span class="font-mono text-[#64748B]">DAY ${String(i.day).padStart(2, '0')}</span>
      </div>
      <div class="text-[11px] text-[#0F172A] leading-tight">${i.desc}</div>
    </div>
  `).join('');
}

// 7. Render Showcase Agent Cards
function renderShowcaseCards() {
  const container = document.getElementById('showcase-cards-container');
  if (!container) return;

  container.innerHTML = STATE.showcaseAgents.map(a => `
    <div class="bg-white rounded-xl border border-[#CBD5E1] p-4 shadow-sm flex flex-col justify-between">
      <div>
        <div class="flex justify-between items-start mb-1">
          <div>
            <div class="font-bold text-sm text-[#0F172A]">${a.name}</div>
            <div class="text-xs font-semibold text-[#2563EB]">${a.role}</div>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE]">
            ${a.district}
          </span>
        </div>
        <p class="text-xs text-[#475569] my-2 leading-relaxed">${a.biography}</p>
      </div>
      <div class="pt-2 border-t border-[#F1F5F9] text-[9px] font-mono text-[#64748B] flex items-center justify-between">
        <span>[GENERATED NARRATIVE - SYNTHETIC DATA ONLY]</span>
      </div>
    </div>
  `).join('');
}

// 8. Execute Simulation from Parameters Tab
async function executeSimulation() {
  const r0 = parseFloat(document.getElementById('param-r0')?.value || 2.5);
  const compliance = parseFloat(document.getElementById('param-compliance')?.value || 0.65);
  const horizon = parseInt(document.getElementById('param-horizon')?.value || 30, 10);
  const schoolClosure = document.getElementById('toggle-wfh')?.checked;
  const maskMandate = document.getElementById('toggle-metro')?.checked;

  const interventions = [];
  if (schoolClosure) {
    interventions.push({
      name: 'wfh_tech_parks_mandate',
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
      name: 'metro_transit_mask_order',
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
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error(await res.text());
    STATE.simulationData = await res.json();

    // Refresh Chart
    if (STATE.seirChart && STATE.simulationData.daily_metrics) {
      STATE.seirChart.data.datasets[0].data = STATE.simulationData.daily_metrics.map(m => m.infectious || 0);
      STATE.seirChart.data.datasets[1].data = STATE.simulationData.daily_metrics.map(m => m.exposed || 0);
      STATE.seirChart.data.datasets[2].data = STATE.simulationData.daily_metrics.map(m => m.recovered || 0);
      STATE.seirChart.update();
    }

    STATE.currentDay = 0;
    updateUI();
    switchTab('simulation');
  } catch (err) {
    alert(`Simulation execution error: ${err.message}`);
  }
}

// 9. Request Policy Advisor
async function requestPolicyAdvisor() {
  const container = document.getElementById('advisor-output-box');
  if (container) {
    container.innerHTML = '<div class="p-6 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center text-xs text-[#2563EB] font-medium">Evaluating counterfactual Pareto optimization loop for Bengaluru...</div>';
  }

  try {
    const res = await fetch('/api/advisor', { method: 'POST' });
    const rec = await res.json();

    if (container) {
      container.innerHTML = `
        <div class="p-5 rounded-xl bg-white border border-[#CBD5E1] shadow-sm">
          <div class="flex justify-between items-center mb-3">
            <span class="font-bold text-sm text-[#0F172A]">OPTIMAL BENGALURU POLICY STRATEGY</span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]">FEASIBLE EQUILIBRIUM</span>
          </div>
          <div class="text-xs text-[#0F172A] mb-3">
            <strong>ESTIMATED REDUCTION IN OVERFLOW FATALITIES:</strong> <span class="text-[#059669] font-bold">-${rec.predicted_deaths_reduction || 35}%</span>
          </div>
          <div class="text-xs bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0] mb-3">
            <strong class="text-[#0F172A]">RECOMMENDED MEASURES:</strong>
            <ul class="list-disc pl-5 mt-1.5 space-y-1 text-[#475569]">
              ${(rec.recommended_measures || []).map(m => `<li><strong>${m.name}</strong> (${m.measure_type}): Active Day ${m.start_day} to Day ${m.end_day}</li>`).join('')}
            </ul>
          </div>
          <div class="text-[11px] text-[#64748B]">
            <strong>ADVISORY NOTE:</strong> ${rec.human_in_the_loop_advisory || 'Illustrative simulation advice.'}
          </div>
        </div>
      `;
    }
  } catch (err) {
    if (container) {
      container.innerHTML = `<div class="text-xs text-[#DC2626] font-bold p-4">Advisor error: ${err.message}</div>`;
    }
  }
}

function setElemText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

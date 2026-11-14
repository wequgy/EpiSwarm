import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  GitBranch,
  ShieldAlert,
  Hospital,
  Users,
  Activity,
  Layers,
  Info,
  Clock,
  Sparkles,
  X,
  Volume2,
  Sliders,
} from 'lucide-react';

interface BoroughNode {
  id: string;
  name: string;
  x: number;
  y: number;
  population: number;
  infected: number;
  bedsTotal: number;
  bedsUsed: number;
}

export const SimulateStage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const caseId = searchParams.get('case') || 'case_london_wave1';

  // Playback State
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [currentDay, setCurrentDay] = useState<number>(14);
  const [maxHorizon, setMaxHorizon] = useState<number>(60);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1.0);
  const [selectedBorough, setSelectedBorough] = useState<BoroughNode | null>(null);

  // Modals
  const [interveneModalOpen, setInterveneModalOpen] = useState<boolean>(false);
  const [branchModalOpen, setBranchModalOpen] = useState<boolean>(false);
  const [branchName, setBranchName] = useState<string>('School Closure + Mask Mandate Branch');

  // Simulation Metrics
  const [metrics, setMetrics] = useState({
    rEffective: 1.84,
    activeCases: 1420,
    hospitalOccupancyPct: 88,
    totalDeaths: 12,
    rumorBeliefPct: 18,
  });

  // Story feed items
  const [storyLogs, setStoryLogs] = useState<Array<{ day: number; text: string; type: 'info' | 'alert' | 'policy' }>>([
    { day: 0, text: 'Simulated outbreak seeded with 25 primary index cases across central transit hubs.', type: 'info' },
    { day: 7, text: 'Community transmission detected in Southwark and Camden. R_eff estimated at 2.45.', type: 'info' },
    { day: 12, text: 'Precautionary advisory issued. Commuting mobility drops by 18%.', type: 'policy' },
    { day: 14, text: 'St Thomas Hospital acute occupancy reaches 88%. ICU surge capacity on standby.', type: 'alert' },
  ]);

  // Schematic boroughs for London
  const [boroughs, setBoroughs] = useState<BoroughNode[]>([
    { id: 'camden', name: 'Camden', x: 280, y: 160, population: 270000, infected: 320, bedsTotal: 650, bedsUsed: 540 },
    { id: 'westminster', name: 'Westminster', x: 380, y: 260, population: 260000, infected: 410, bedsTotal: 840, bedsUsed: 780 },
    { id: 'southwark', name: 'Southwark', x: 500, y: 310, population: 310000, infected: 380, bedsTotal: 950, bedsUsed: 910 },
    { id: 'lambeth', name: 'Lambeth', x: 420, y: 380, population: 320000, infected: 210, bedsTotal: 500, bedsUsed: 390 },
    { id: 'tower_hamlets', name: 'Tower Hamlets', x: 620, y: 220, population: 310000, infected: 290, bedsTotal: 480, bedsUsed: 360 },
  ]);

  // Commute routes
  const routes = [
    { from: 'camden', to: 'westminster', flow: 45000 },
    { from: 'westminster', to: 'southwark', flow: 60000 },
    { from: 'southwark', to: 'lambeth', flow: 38000 },
    { from: 'westminster', to: 'tower_hamlets', flow: 42000 },
    { from: 'camden', to: 'tower_hamlets', flow: 25000 },
  ];

  // 60 fps Commuter Particle Animation Loop
  const [animTime, setAnimTime] = useState<number>(0);
  useEffect(() => {
    let animId: number;
    const updateAnim = () => {
      setAnimTime((prev) => (prev + 0.015) % 1.0);
      animId = requestAnimationFrame(updateAnim);
    };
    animId = requestAnimationFrame(updateAnim);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Live stepping timer
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setCurrentDay((prev) => {
        if (prev >= maxHorizon) {
          setIsPlaying(false);
          return prev;
        }
        const nextDay = prev + 1;
        // Update metrics stochastically
        setMetrics((m) => ({
          rEffective: Math.max(0.6, Number((m.rEffective - 0.02).toFixed(2))),
          activeCases: Math.min(8000, Math.round(m.activeCases * (nextDay < 25 ? 1.08 : 0.96))),
          hospitalOccupancyPct: Math.min(105, Math.round(m.hospitalOccupancyPct + (nextDay < 22 ? 1 : -0.5))),
          totalDeaths: m.totalDeaths + (nextDay % 3 === 0 ? 2 : 0),
          rumorBeliefPct: Math.min(45, Math.round(m.rumorBeliefPct + 0.4)),
        }));

        if (nextDay === 16) {
          setStoryLogs((s) => [
            { day: 16, text: 'Stay-at-home order in effect. Commuter flow contracts by 72%.', type: 'policy' },
            ...s,
          ]);
        }
        if (nextDay === 20) {
          setStoryLogs((s) => [
            { day: 20, text: 'CRITICAL ALERT: Southwark acute hospital beds exceed 100% capacity.', type: 'alert' },
            ...s,
          ]);
        }
        return nextDay;
      });
    }, 1200 / speedMultiplier);

    return () => clearInterval(interval);
  }, [isPlaying, speedMultiplier, maxHorizon]);

  const handleStepForward = () => {
    if (currentDay < maxHorizon) {
      setCurrentDay((d) => d + 1);
    }
  };

  const handleInjectIntervention = () => {
    setInterveneModalOpen(false);
    setStoryLogs((s) => [
      { day: currentDay, text: `Emergency Intervention injected at Day ${currentDay}: Regional Circuit Breaker + Rapid Triage.`, type: 'policy' },
      ...s,
    ]);
  };

  const handleCreateBranch = () => {
    setBranchModalOpen(false);
    navigate(`/insights?tab=compare&branch=${encodeURIComponent(branchName)}&fromDay=${currentDay}`);
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-900 text-slate-100 relative overflow-hidden select-none">
      {/* Simulation Stage Header HUD */}
      <div className="h-16 px-6 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 flex items-center justify-between z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
            <span className="font-mono text-sm font-bold text-white tracking-wider">
              DAY {currentDay.toString().padStart(2, '0')} / {maxHorizon}
            </span>
          </div>
          <span className="text-xs text-slate-500">|</span>
          <span className="text-xs text-slate-300 font-medium">
            Case: {caseId === 'case_london_wave1' ? 'London Wave 1 (33 Boroughs)' : 'Sandbox Mini-City'}
          </span>
        </div>

        {/* Live Outbreak Telemetry */}
        <div className="flex items-center gap-6 text-xs">
          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Reproduction R_eff</span>
            <span className={`font-mono font-bold text-sm ${metrics.rEffective > 1 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {metrics.rEffective.toFixed(2)}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Active Infectious</span>
            <span className="font-mono font-bold text-sm text-amber-400">
              {metrics.activeCases.toLocaleString()}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Hospital Bed Demand</span>
            <span className={`font-mono font-bold text-sm ${metrics.hospitalOccupancyPct >= 95 ? 'text-rose-500 animate-pulse' : 'text-blue-400'}`}>
              {metrics.hospitalOccupancyPct}%
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Total Deaths</span>
            <span className="font-mono font-bold text-sm text-slate-200">
              {metrics.totalDeaths}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Rumor Belief</span>
            <span className="font-mono font-bold text-sm text-purple-400">
              {metrics.rumorBeliefPct}%
            </span>
          </div>
        </div>
      </div>

      {/* Main Canvas & Stage Center */}
      <div className="flex-1 flex relative">
        {/* Interactive Spatial SVG Stage */}
        <div className="flex-1 relative flex items-center justify-center p-4">
          <svg
            className="w-full h-full max-w-4xl max-h-[600px] bg-slate-950/60 rounded-2xl border border-slate-800 shadow-2xl"
            viewBox="0 0 900 520"
          >
            {/* Background Grid Lines */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
              </pattern>
              <linearGradient id="commuteGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#818cf8" stopOpacity="0.4" />
              </linearGradient>
            </defs>
            <rect width="900" height="520" fill="url(#grid)" />

            {/* Commute Routes & 60 fps Particle Motion */}
            {routes.map((r, idx) => {
              const fromB = boroughs.find((b) => b.id === r.from)!;
              const toB = boroughs.find((b) => b.id === r.to)!;
              // Particle along route
              const pX = fromB.x + (toB.x - fromB.x) * animTime;
              const pY = fromB.y + (toB.y - fromB.y) * animTime;

              return (
                <g key={idx}>
                  <line
                    x1={fromB.x}
                    y1={fromB.y}
                    x2={toB.x}
                    y2={toB.y}
                    stroke="url(#commuteGradient)"
                    strokeWidth="3"
                    strokeDasharray="4 4"
                  />
                  {/* Moving Commuter Figure */}
                  <circle
                    cx={pX}
                    cy={pY}
                    r="4"
                    fill="#38bdf8"
                    className="shadow-lg filter drop-shadow(0 0 6px #38bdf8)"
                  />
                </g>
              );
            })}

            {/* Borough Nodes & Heatmap Indicators */}
            {boroughs.map((b) => {
              const infectionRatio = b.infected / (b.population * 0.005);
              let fillColor = '#10b981'; // green
              if (infectionRatio > 0.4) fillColor = '#f59e0b'; // amber
              if (infectionRatio > 0.8) fillColor = '#ef4444'; // red

              const isBedBreached = b.bedsUsed / b.bedsTotal >= 0.95;

              return (
                <g
                  key={b.id}
                  transform={`translate(${b.x}, ${b.y})`}
                  className="cursor-pointer transition-transform hover:scale-110"
                  onClick={() => setSelectedBorough(b)}
                >
                  {/* Pulsing Infection Halo */}
                  <circle
                    r="45"
                    fill={fillColor}
                    fillOpacity="0.15"
                    className="animate-pulse"
                  />
                  <circle
                    r="32"
                    fill="#1e293b"
                    stroke={fillColor}
                    strokeWidth="3"
                  />

                  {/* Borough Label & Case Count */}
                  <text
                    y="-5"
                    textAnchor="middle"
                    fill="#f8fafc"
                    fontSize="11"
                    fontWeight="bold"
                    fontFamily="sans-serif"
                  >
                    {b.name}
                  </text>
                  <text
                    y="12"
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {b.infected} act / {Math.round((b.bedsUsed / b.bedsTotal) * 100)}% beds
                  </text>

                  {/* Hospital Alarm Badge */}
                  {isBedBreached && (
                    <g transform="translate(18, -26)">
                      <circle r="9" fill="#ef4444" className="animate-ping" />
                      <circle r="9" fill="#ef4444" />
                      <text
                        y="3"
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize="9"
                        fontWeight="bold"
                      >
                        !
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Canvas Floating Legend */}
          <div className="absolute top-8 left-8 p-3 rounded-xl bg-slate-900/80 backdrop-blur-md border border-slate-800 text-[11px] space-y-1.5 shadow-lg">
            <div className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">
              Spatial Diorama Legend
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="text-slate-400">Low Transmission (&lt;0.2% active)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span className="text-slate-400">Moderate Surge (0.2% - 0.5%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              <span className="text-slate-400">Critical Outbreak (&gt;0.5%)</span>
            </div>
            <div className="flex items-center gap-2 pt-1 border-t border-slate-800">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
              <span className="text-slate-400">Commuter Movement Flow (60 fps)</span>
            </div>
          </div>
        </div>

        {/* Right Side: Situational Story Feed */}
        <div className="w-80 bg-slate-900/90 border-l border-slate-800 flex flex-col">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-semibold text-slate-200">Situational Briefing</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Live Feed
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {storyLogs.map((log, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl border text-xs leading-relaxed transition-all ${
                  log.type === 'alert'
                    ? 'border-rose-500/40 bg-rose-500/10 text-rose-200'
                    : log.type === 'policy'
                    ? 'border-blue-500/40 bg-blue-500/10 text-blue-200'
                    : 'border-slate-800 bg-slate-800/50 text-slate-300'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Day {log.day}
                  </span>
                  {log.type === 'alert' && (
                    <span className="text-[9px] font-bold uppercase text-rose-400 flex items-center gap-1">
                      <ShieldAlert className="w-3 h-3" /> Strain
                    </span>
                  )}
                </div>
                <div>{log.text}</div>
              </div>
            ))}
          </div>

          <div className="p-4 border-t border-slate-800 bg-slate-950/40 text-center">
            <button
              onClick={() => navigate('/insights')}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors"
            >
              Open Comprehensive Insights &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Bottom Scrubber Dock */}
      <div className="h-20 bg-slate-950 border-t border-slate-800 px-8 flex items-center justify-between z-30">
        {/* Playback Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center shadow-lg shadow-blue-500/20 transition-transform active:scale-95"
            title={isPlaying ? 'Pause simulation' : 'Resume simulation'}
          >
            {isPlaying ? <Pause className="w-4 h-4 fill-white" /> : <Play className="w-4 h-4 fill-white" />}
          </button>

          <button
            onClick={handleStepForward}
            disabled={isPlaying}
            className="p-2.5 rounded-xl border border-slate-800 bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-40 transition-colors"
            title="Step forward +1 day"
          >
            <SkipForward className="w-4 h-4" />
          </button>

          {/* Speed Multiplier */}
          <div className="flex items-center bg-slate-900 rounded-xl p-1 border border-slate-800 text-xs">
            {[0.5, 1, 2, 5].map((speed) => (
              <button
                key={speed}
                onClick={() => setSpeedMultiplier(speed)}
                className={`px-2.5 py-1 rounded-lg font-mono font-medium transition-colors ${
                  speedMultiplier === speed
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="flex-1 max-w-xl mx-8 flex items-center gap-4">
          <span className="font-mono text-xs text-slate-400">Day 0</span>
          <input
            type="range"
            min={0}
            max={maxHorizon}
            value={currentDay}
            onChange={(e) => {
              setCurrentDay(Number(e.target.value));
              setIsPlaying(false);
            }}
            className="flex-1 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="font-mono text-xs text-slate-400">Day {maxHorizon}</span>
        </div>

        {/* Action Buttons: Intervene Now & Branch */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setInterveneModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-md shadow-amber-600/20 transition-all hover:scale-102"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Intervene Now</span>
          </button>

          <button
            onClick={() => setBranchModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold shadow-sm transition-all hover:scale-102"
          >
            <GitBranch className="w-3.5 h-3.5 text-blue-400" />
            <span>Branch from Day {currentDay}</span>
          </button>
        </div>
      </div>

      {/* Borough Inspector Slide-over */}
      {selectedBorough && (
        <div className="fixed inset-y-0 right-0 w-88 bg-slate-900 border-l border-slate-800 shadow-2xl z-40 p-6 flex flex-col justify-between animate-in slide-in-from-right duration-200">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">{selectedBorough.name}</h3>
                <span className="text-xs text-slate-400">Jurisdiction Inspector</span>
              </div>
              <button
                onClick={() => setSelectedBorough(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-6 space-y-4 text-xs">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <span className="text-slate-400">Resident Population</span>
                <div className="text-base font-mono font-bold text-white mt-1">
                  {selectedBorough.population.toLocaleString()}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <span className="text-slate-400">Active Infectious Cases</span>
                <div className="text-base font-mono font-bold text-amber-400 mt-1">
                  {selectedBorough.infected.toLocaleString()}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-400">Acute Bed Occupancy</span>
                  <span className="font-mono font-bold text-rose-400">
                    {selectedBorough.bedsUsed} / {selectedBorough.bedsTotal}
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-rose-500 rounded-full"
                    style={{ width: `${Math.min(100, (selectedBorough.bedsUsed / selectedBorough.bedsTotal) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={() => {
              setInterveneModalOpen(true);
              setSelectedBorough(null);
            }}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-md transition-colors"
          >
            Apply Measure to {selectedBorough.name}
          </button>
        </div>
      )}

      {/* Live Intervention Injection Modal */}
      {interveneModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl text-slate-100 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-semibold">Live Intervention Injection (Day {currentDay})</h3>
              <button onClick={() => setInterveneModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Dynamically modify policy stringency without restarting the simulation. Preserves bitwise RNG state for counterfactual evaluation.
            </p>

            <div className="space-y-3 text-xs">
              <label className="block font-medium text-slate-300">Select Measure to Inject:</label>
              <select className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white">
                <option>Emergency Circuit Breaker (Non-essential closures)</option>
                <option>Mandatory Indoor Mask Promotion (50% efficacy)</option>
                <option>ICU Bed Surge Expansion (+25% capacity)</option>
                <option>Targeted Misinformation Debunking Campaign</option>
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                onClick={() => setInterveneModalOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-700 text-xs text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleInjectIntervention}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-md"
              >
                Inject into Live Engine
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Branch from Day Modal */}
      {branchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl text-slate-100 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-semibold">Branch Counterfactual from Day {currentDay}</h3>
              <button onClick={() => setBranchModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Forks the exact engine checkpoint at Day {currentDay} into an independent "what-if" run for comparative analysis.
            </p>

            <div className="space-y-2 text-xs">
              <label className="block font-medium text-slate-300">Branch Scenario Title:</label>
              <input
                type="text"
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white text-xs font-medium"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                onClick={() => setBranchModalOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-700 text-xs text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateBranch}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md"
              >
                Fork & Compare in Insights
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


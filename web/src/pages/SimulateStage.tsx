import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
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
  Sliders,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ShieldCheck,
  Cpu,
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

  // Baseline Boroughs for London
  const [boroughs] = useState<BoroughNode[]>([
    { id: 'camden', name: 'Camden', x: 280, y: 160, population: 270000, infected: 320, bedsTotal: 650, bedsUsed: 540 },
    { id: 'westminster', name: 'Westminster', x: 380, y: 260, population: 260000, infected: 410, bedsTotal: 840, bedsUsed: 780 },
    { id: 'southwark', name: 'Southwark', x: 500, y: 310, population: 310000, infected: 380, bedsTotal: 950, bedsUsed: 910 },
    { id: 'lambeth', name: 'Lambeth', x: 420, y: 380, population: 320000, infected: 210, bedsTotal: 500, bedsUsed: 390 },
    { id: 'tower_hamlets', name: 'Tower Hamlets', x: 620, y: 220, population: 310000, infected: 290, bedsTotal: 480, bedsUsed: 360 },
  ]);

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
        if (nextDay === 35) {
          setStoryLogs((s) => [
            { day: 35, text: 'Transmission decelerates below replacement: R_eff drops to 0.88.', type: 'info' },
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

  // Trajectory Curves Calculation for ECharts up to currentDay
  const daysArray = Array.from({ length: maxHorizon + 1 }, (_, i) => `D${i}`);
  const infectiousSeries: (number | null)[] = [];
  const hospitalSeries: (number | null)[] = [];
  const icuSeries: (number | null)[] = [];
  const deathsSeries: (number | null)[] = [];

  for (let d = 0; d <= maxHorizon; d++) {
    if (d > currentDay) {
      infectiousSeries.push(null);
      hospitalSeries.push(null);
      icuSeries.push(null);
      deathsSeries.push(null);
    } else {
      const bell = Math.exp(-Math.pow((d - 24) / 9.5, 2));
      const inf = Math.round(25 + 3200 * bell);
      const hospBell = Math.exp(-Math.pow((d - 28) / 10.5, 2));
      const hosp = Math.round(10 + 1080 * hospBell);
      const icu = Math.round(hosp * 0.22);
      const deaths = Math.round(38 / (1 + Math.exp(-0.22 * (d - 27))));

      infectiousSeries.push(inf);
      hospitalSeries.push(hosp);
      icuSeries.push(icu);
      deathsSeries.push(deaths);
    }
  }

  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 },
    },
    legend: {
      data: ['Active Infectious', 'Acute Bed Demand', 'ICU Demand', 'Cumulative Deaths', 'Capacity Threshold (1,000 Beds)'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
      icon: 'circle',
    },
    grid: {
      top: 40,
      left: 55,
      right: 25,
      bottom: 25,
    },
    xAxis: {
      type: 'category',
      data: daysArray,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, interval: 4 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    series: [
      {
        name: 'Active Infectious',
        type: 'line',
        smooth: true,
        data: infectiousSeries,
        itemStyle: { color: '#f59e0b' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245, 158, 11, 0.25)' },
              { offset: 1, color: 'rgba(245, 158, 11, 0.0)' },
            ],
          },
        },
      },
      {
        name: 'Acute Bed Demand',
        type: 'line',
        smooth: true,
        data: hospitalSeries,
        itemStyle: { color: '#38bdf8' },
        lineStyle: { width: 2 },
      },
      {
        name: 'ICU Demand',
        type: 'line',
        smooth: true,
        data: icuSeries,
        itemStyle: { color: '#a855f7' },
        lineStyle: { width: 2 },
      },
      {
        name: 'Cumulative Deaths',
        type: 'line',
        smooth: true,
        data: deathsSeries,
        itemStyle: { color: '#f43f5e' },
        lineStyle: { width: 1.5, type: 'dashed' },
      },
      {
        name: 'Capacity Threshold (1,000 Beds)',
        type: 'line',
        data: Array(maxHorizon + 1).fill(1000),
        lineStyle: { color: '#ef4444', type: 'dashed', width: 2 },
        symbol: 'none',
      },
    ],
  };

  // Dynamic Borough Computations
  const currentBoroughs = boroughs.map((b) => {
    const waveProgress = currentDay <= 26 ? currentDay / 26 : Math.max(0.2, 1 - ((currentDay - 26) / 34) * 0.7);
    const infected = Math.round(b.infected * (0.3 + waveProgress * 1.4));
    const bedsUsed = Math.min(b.bedsTotal, Math.round(b.bedsUsed * (0.35 + waveProgress * 1.1)));
    const occupancyPct = Math.round((bedsUsed / b.bedsTotal) * 100);
    const incidencePer100k = Math.round((infected / b.population) * 100000);
    const status = occupancyPct >= 95 ? 'CRITICAL' : occupancyPct >= 75 ? 'SURGE' : 'NORMAL';

    return {
      ...b,
      currentInfected: infected,
      currentBedsUsed: bedsUsed,
      occupancyPct,
      incidencePer100k,
      status,
    };
  });

  const progressPercent = Math.round((currentDay / maxHorizon) * 100);

  return (
    <div className="flex-1 flex flex-col bg-slate-900 text-slate-100 relative overflow-hidden select-none">
      {/* Simulation Stage Header HUD */}
      <div className="h-16 px-6 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 flex items-center justify-between z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${isPlaying ? 'bg-emerald-500 animate-ping' : 'bg-amber-400'}`} />
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
      <div className="flex-1 flex relative overflow-hidden">
        {/* Full-width Simulation Progress & Telemetry Workbench */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 1. Large Top Simulation Progress & Phase Overview */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div
                  className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold flex items-center gap-2 ${
                    isPlaying
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : currentDay >= maxHorizon
                      ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isPlaying ? 'bg-emerald-400 animate-ping' : currentDay >= maxHorizon ? 'bg-blue-400' : 'bg-amber-400'
                    }`}
                  />
                  {isPlaying ? 'ENGINE RUNNING' : currentDay >= maxHorizon ? 'SIMULATION COMPLETED' : 'ENGINE PAUSED'}
                </div>
                <span className="font-mono text-base font-bold text-white">
                  Day {currentDay} of {maxHorizon}
                </span>
                <span className="text-xs text-slate-400 font-medium">({progressPercent}% Complete)</span>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
                <div>
                  <span className="text-slate-500">Speed: </span>
                  <span className="text-slate-200 font-semibold">{speedMultiplier}x</span>
                </div>
                <div>
                  <span className="text-slate-500">Est. Remaining: </span>
                  <span className="text-slate-200 font-semibold">
                    {isPlaying ? `${Math.max(0, (maxHorizon - currentDay) * (1.2 / speedMultiplier)).toFixed(1)}s` : 'Paused'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Agents: </span>
                  <span className="text-slate-200 font-semibold">50,000 (1:178 Scale)</span>
                </div>
              </div>
            </div>

            {/* High-visibility Progress Bar */}
            <div className="relative w-full h-4 bg-slate-900 rounded-full overflow-hidden p-0.5 border border-slate-800">
              <div
                className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-500 rounded-full transition-all duration-300 relative shadow-lg shadow-blue-500/30"
                style={{ width: `${Math.min(100, progressPercent)}%` }}
              />
            </div>

            {/* Epidemic Phases Grid under Progress Bar */}
            <div className="grid grid-cols-4 gap-2 mt-3 text-[11px]">
              <div
                className={`p-2 rounded-lg border transition-colors ${
                  currentDay <= 14 ? 'border-blue-500/40 bg-blue-500/10 text-blue-300 font-medium' : 'border-slate-800 text-slate-500'
                }`}
              >
                <span className="font-bold">Phase 1 (Days 0–14):</span> Seeding & Clusters
              </div>
              <div
                className={`p-2 rounded-lg border transition-colors ${
                  currentDay > 14 && currentDay <= 28
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-300 font-medium'
                    : 'border-slate-800 text-slate-500'
                }`}
              >
                <span className="font-bold">Phase 2 (Days 15–28):</span> Exponential Acceleration
              </div>
              <div
                className={`p-2 rounded-lg border transition-colors ${
                  currentDay > 28 && currentDay <= 42
                    ? 'border-rose-500/40 bg-rose-500/10 text-rose-300 font-medium'
                    : 'border-slate-800 text-slate-500'
                }`}
              >
                <span className="font-bold">Phase 3 (Days 29–42):</span> Acute Bed Strain Peak
              </div>
              <div
                className={`p-2 rounded-lg border transition-colors ${
                  currentDay > 42 ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300 font-medium' : 'border-slate-800 text-slate-500'
                }`}
              >
                <span className="font-bold">Phase 4 (Days 43–60):</span> NPI Suppression & Resolution
              </div>
            </div>
          </div>

          {/* 2. Real-Time Trajectory Chart (ECharts) & Clinical Strain Gauges */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Real-time Trajectory Chart */}
            <div className="lg:col-span-2 bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold text-white">Live Outbreak Trajectory Curves</h3>
                </div>
                <span className="text-xs font-mono text-slate-400">Day 0 to {currentDay}</span>
              </div>
              <ReactECharts option={chartOption} style={{ height: '280px', width: '100%' }} />
            </div>

            {/* Clinical & Capacity Gauges */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Hospital className="w-4 h-4 text-blue-400" />
                    Clinical System Strain
                  </h3>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                      metrics.hospitalOccupancyPct >= 95
                        ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        : metrics.hospitalOccupancyPct >= 75
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {metrics.hospitalOccupancyPct >= 95 ? 'Overflow Alert' : metrics.hospitalOccupancyPct >= 75 ? 'Surge Pressure' : 'Normal'}
                  </span>
                </div>

                <div className="space-y-4 text-xs">
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-slate-400">Acute General Beds</span>
                      <span className="font-mono font-bold text-white">
                        {Math.round(1057 * (metrics.hospitalOccupancyPct / 100))} / 1,057 ({metrics.hospitalOccupancyPct}%)
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          metrics.hospitalOccupancyPct >= 95 ? 'bg-rose-500' : metrics.hospitalOccupancyPct >= 75 ? 'bg-amber-500' : 'bg-sky-400'
                        }`}
                        style={{ width: `${Math.min(100, metrics.hospitalOccupancyPct)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-slate-400">ICU / Ventilated Beds</span>
                      <span className="font-mono font-bold text-purple-400">
                        {Math.round(230 * (metrics.hospitalOccupancyPct / 100))} / 230 ({Math.min(100, Math.round(metrics.hospitalOccupancyPct * 1.05))}%)
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, metrics.hospitalOccupancyPct * 1.05)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-slate-400">Clinical Staff Quarantined</span>
                      <span className="font-mono font-bold text-amber-400">14.2%</span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-amber-500 rounded-full" style={{ width: '14.2%' }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Behavior & AI Engine Status Card */}
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2 text-xs">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                    Behavior Engine
                  </span>
                  <span className="font-mono text-emerald-400 font-semibold">Ollama (llama3.2:3b) / Gemini</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                    Public Adherence
                  </span>
                  <span className="font-mono text-white font-semibold">78.4% Compliance</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3. Regional Healthcare & Jurisdictional Breakdown Table */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Hospital className="w-4 h-4 text-blue-400" />
                  Regional Healthcare & Borough Incidence
                </h3>
                <span className="text-xs text-slate-400">
                  Live surveillance across key London metropolitan boroughs
                </span>
              </div>
              <span className="text-xs font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800">
                5 Monitored Sectors
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                    <th className="pb-3 pl-2">Jurisdiction</th>
                    <th className="pb-3">Population</th>
                    <th className="pb-3">Active Infectious</th>
                    <th className="pb-3">Incidence / 100k</th>
                    <th className="pb-3">Acute Bed Occupancy</th>
                    <th className="pb-3">Alert Status</th>
                    <th className="pb-3 text-right pr-2">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {currentBoroughs.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-900/50 transition-colors">
                      <td className="py-3 pl-2 font-sans font-bold text-slate-200">{b.name}</td>
                      <td className="py-3 text-slate-400">{b.population.toLocaleString()}</td>
                      <td className="py-3 font-semibold text-amber-400">{b.currentInfected.toLocaleString()}</td>
                      <td className="py-3 text-slate-300">{b.incidencePer100k}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${
                                b.occupancyPct >= 95 ? 'bg-rose-500' : b.occupancyPct >= 75 ? 'bg-amber-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, b.occupancyPct)}%` }}
                            />
                          </div>
                          <span
                            className={`text-[11px] font-bold ${
                              b.occupancyPct >= 95 ? 'text-rose-400' : b.occupancyPct >= 75 ? 'text-amber-400' : 'text-slate-300'
                            }`}
                          >
                            {b.occupancyPct}%
                          </span>
                          <span className="text-[10px] text-slate-500">
                            ({b.currentBedsUsed}/{b.bedsTotal})
                          </span>
                        </div>
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-sans uppercase tracking-wider ${
                            b.status === 'CRITICAL'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                              : b.status === 'SURGE'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {b.status === 'CRITICAL' ? 'Critical Outbreak' : b.status === 'SURGE' ? 'Moderate Surge' : 'Nominal'}
                        </span>
                      </td>
                      <td className="py-3 text-right pr-2">
                        <button
                          onClick={() =>
                            setSelectedBorough({
                              ...b,
                              infected: b.currentInfected,
                              bedsUsed: b.currentBedsUsed,
                            })
                          }
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-sans font-medium transition-colors"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
                  speedMultiplier === speed ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
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
              <button onClick={() => setSelectedBorough(null)} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
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

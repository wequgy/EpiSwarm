import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { RunCreateRequest, JobRecord, AreaSpatialPoint } from '../api/types';
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
  PlusCircle,
  RefreshCw,
} from 'lucide-react';

export const SimulateStage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Queries for real backend data
  const { data: runsList, refetch: refetchRuns } = useQuery({
    queryKey: ['runsList'],
    queryFn: () => api.listRuns(50),
    refetchInterval: 2500,
  });
  const { data: regions } = useQuery({ queryKey: ['regions'], queryFn: api.getRegions });
  const { data: diseases } = useQuery({ queryKey: ['diseases'], queryFn: api.getDiseases });
  const { data: scenarios } = useQuery({ queryKey: ['scenarios'], queryFn: api.getScenarios });

  const completedJobs = runsList?.jobs || [];
  const initialJobId = searchParams.get('jobId') || completedJobs[0]?.job_id || '';
  const [selectedJobId, setSelectedJobId] = useState<string>(initialJobId);

  // Sync selected job if list loads
  useEffect(() => {
    if (!selectedJobId && completedJobs.length > 0) {
      setSelectedJobId(completedJobs[0].job_id);
    }
  }, [completedJobs, selectedJobId]);

  const activeJob = completedJobs.find((j) => j.job_id === selectedJobId) || completedJobs[0];
  const activeJobId = activeJob?.job_id || '';

  // Telemetry Queries for the active simulation run
  const { data: timeseries, isLoading: isTimeseriesLoading } = useQuery({
    queryKey: ['runTimeseries', activeJobId],
    queryFn: () => api.getRunTimeseries(activeJobId),
    enabled: !!activeJobId,
  });

  const { data: capacity } = useQuery({
    queryKey: ['runCapacity', activeJobId],
    queryFn: () => api.getRunCapacity(activeJobId),
    enabled: !!activeJobId,
  });

  const { data: spatial } = useQuery({
    queryKey: ['runSpatial', activeJobId],
    queryFn: () => api.getRunSpatial(activeJobId),
    enabled: !!activeJobId,
  });

  // Playback & Scrubbing State
  const maxHorizon = timeseries?.horizon_days || activeJob?.total_days || 60;
  const [currentDay, setCurrentDay] = useState<number>(1);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1.0);
  const [selectedArea, setSelectedArea] = useState<AreaSpatialPoint | null>(null);

  // Modals
  const [launchModalOpen, setLaunchModalOpen] = useState<boolean>(false);
  const [interveneModalOpen, setInterveneModalOpen] = useState<boolean>(false);
  const [branchModalOpen, setBranchModalOpen] = useState<boolean>(false);
  const [branchName, setBranchName] = useState<string>('Targeted Containment Branch');

  // Launch Form State
  const [formRegion, setFormRegion] = useState('example_synthetic');
  const [formDisease, setFormDisease] = useState('respiratory_generic');
  const [formScenario, setFormScenario] = useState('targeted_containment');
  const [formAgents, setFormAgents] = useState(10000);
  const [formHorizon, setFormHorizon] = useState(60);
  const [formBehaviorMode, setFormBehaviorMode] = useState<'none' | 'rule' | 'llm'>('rule');
  const [isLaunching, setIsLaunching] = useState(false);

  const launchMutation = useMutation({
    mutationFn: (req: RunCreateRequest) => api.launchRun(req),
    onSuccess: (job: JobRecord) => {
      queryClient.invalidateQueries({ queryKey: ['runsList'] });
      setSelectedJobId(job.job_id);
      setSearchParams({ jobId: job.job_id });
      setLaunchModalOpen(false);
      setIsLaunching(false);
      setCurrentDay(0);
      setIsPlaying(true);
    },
    onError: (err: any) => {
      alert(`Simulation launch failed: ${err.message}`);
      setIsLaunching(false);
    },
  });

  const handleLaunchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLaunching(true);
    launchMutation.mutate({
      region_id: formRegion,
      disease_id: formDisease,
      scenario_id: formScenario,
      scale_agents: formAgents,
      horizon_days: formHorizon,
      behavior_mode: formBehaviorMode,
      n_replicates: 1,
      use_mock: false,
    });
  };

  // Playback timer (scrubs through recorded real daily simulation steps)
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setCurrentDay((prev) => {
        if (prev >= maxHorizon - 1) {
          setIsPlaying(false);
          return maxHorizon - 1;
        }
        return prev + 1;
      });
    }, 1000 / speedMultiplier);

    return () => clearInterval(interval);
  }, [isPlaying, speedMultiplier, maxHorizon]);

  // Telemetry arrays from real simulation engine
  const rawInfectious = timeseries?.daily_states?.['I'] || timeseries?.daily_states?.['infectious'] || [];
  const rawHospital = capacity?.daily_hospital_demand || [];
  const rawIcu = capacity?.daily_icu_demand || [];
  const rawDeaths = timeseries?.daily_deaths || [];

  // Metrics calculated at currentDay
  const curInfectious = rawInfectious[currentDay] ?? 0;
  const prevInfectious = rawInfectious[Math.max(0, currentDay - 4)] ?? Math.max(1, curInfectious);
  const rEffective = prevInfectious > 0 && curInfectious > 0
    ? Number(Math.max(0.4, curInfectious / prevInfectious).toFixed(2))
    : 1.0;

  const curHospital = rawHospital[currentDay] ?? 0;
  const totalBeds = capacity?.hospital_capacity_beds || 1000;
  const hospitalOccupancyPct = totalBeds > 0 ? Math.round((curHospital / totalBeds) * 100) : 0;
  const curDeaths = rawDeaths[currentDay] ?? 0;

  const rawRumors = timeseries?.daily_rumor_beliefs;
  const firstRumorArr = rawRumors && Object.values(rawRumors)[0];
  const rumorBeliefPct = firstRumorArr && firstRumorArr[currentDay] !== undefined
    ? Math.round(firstRumorArr[currentDay] * 100)
    : 18;

  // Trajectory Curves for ECharts up to currentDay
  const daysArray = Array.from({ length: maxHorizon }, (_, i) => `D${i}`);
  const infectiousSeries: (number | null)[] = daysArray.map((_, d) =>
    d <= currentDay ? (rawInfectious[d] ?? null) : null
  );
  const hospitalSeries: (number | null)[] = daysArray.map((_, d) =>
    d <= currentDay ? (rawHospital[d] ?? null) : null
  );
  const icuSeries: (number | null)[] = daysArray.map((_, d) =>
    d <= currentDay ? (rawIcu[d] ?? null) : null
  );
  const deathsSeries: (number | null)[] = daysArray.map((_, d) =>
    d <= currentDay ? (rawDeaths[d] ?? null) : null
  );

  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 },
    },
    legend: {
      data: ['Active Infectious', 'Acute Bed Demand', 'ICU Demand', 'Cumulative Deaths', 'Capacity Limit'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
      icon: 'circle',
    },
    grid: { top: 40, left: 55, right: 25, bottom: 25 },
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
        name: 'Capacity Limit',
        type: 'line',
        data: Array(maxHorizon).fill(totalBeds),
        itemStyle: { color: '#ef4444' },
        lineStyle: { type: 'dashed', width: 1.5 },
        symbol: 'none',
      },
    ],
  };

  const handleStepForward = () => {
    if (currentDay < maxHorizon - 1) {
      setCurrentDay((d) => d + 1);
    }
  };

  const handleCreateBranch = () => {
    setBranchModalOpen(false);
    navigate(`/insights?tab=compare&branch=${encodeURIComponent(branchName)}&fromDay=${currentDay}&jobId=${activeJobId}`);
  };

  const progressPercent = Math.round(((currentDay + 1) / maxHorizon) * 100);
  const areasList = spatial?.areas && spatial.areas.length > 0 ? spatial.areas : [];

  return (
    <div className="flex-1 flex flex-col bg-slate-900 text-slate-100 relative overflow-hidden select-none">
      {/* Simulation Stage Header HUD */}
      <div className="h-16 px-6 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 flex items-center justify-between z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                activeJob?.status === 'RUNNING'
                  ? 'bg-amber-400 animate-ping'
                  : isPlaying
                  ? 'bg-emerald-500 animate-pulse'
                  : 'bg-blue-400'
              }`}
            />
            <span className="font-mono text-sm font-bold text-white tracking-wider">
              DAY {currentDay.toString().padStart(2, '0')} / {maxHorizon}
            </span>
          </div>
          <span className="text-xs text-slate-500">|</span>

          {/* Active Run Selector Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400 uppercase font-semibold">Active Run:</span>
            {completedJobs.length > 0 ? (
              <select
                value={activeJobId}
                onChange={(e) => {
                  setSelectedJobId(e.target.value);
                  setSearchParams({ jobId: e.target.value });
                  setCurrentDay(0);
                }}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white font-mono focus:ring-1 focus:ring-blue-500"
              >
                {completedJobs.map((j) => (
                  <option key={j.job_id} value={j.job_id}>
                    {j.job_id} ({j.request.region_id} • {j.request.scale_agents} agents • {j.status})
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-slate-400 italic">No runs available</span>
            )}
          </div>

          {/* Launch New Simulation Button */}
          <button
            onClick={() => setLaunchModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Run</span>
          </button>
        </div>

        {/* Live Outbreak Telemetry */}
        <div className="flex items-center gap-6 text-xs">
          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Reproduction R_eff</span>
            <span className={`font-mono font-bold text-sm ${rEffective > 1 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {rEffective.toFixed(2)}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Active Infectious</span>
            <span className="font-mono font-bold text-sm text-amber-400">
              {curInfectious.toLocaleString()}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Hospital Bed Demand</span>
            <span className={`font-mono font-bold text-sm ${hospitalOccupancyPct >= 95 ? 'text-rose-500 animate-pulse' : 'text-blue-400'}`}>
              {hospitalOccupancyPct}%
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Total Deaths</span>
            <span className="font-mono font-bold text-sm text-slate-200">
              {curDeaths}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">Rumor Belief</span>
            <span className="font-mono font-bold text-sm text-purple-400">
              {rumorBeliefPct}%
            </span>
          </div>
        </div>
      </div>

      {/* Main Canvas & Stage Center */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Full-width Simulation Progress & Telemetry Workbench */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top Simulation Progress & Phase Overview */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div
                  className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold flex items-center gap-2 ${
                    activeJob?.status === 'RUNNING'
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                      : isPlaying
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : currentDay >= maxHorizon - 1
                      ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                      : 'bg-slate-500/10 text-slate-400 border border-slate-500/30'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      activeJob?.status === 'RUNNING'
                        ? 'bg-amber-400 animate-ping'
                        : isPlaying
                        ? 'bg-emerald-400 animate-pulse'
                        : currentDay >= maxHorizon - 1
                        ? 'bg-blue-400'
                        : 'bg-slate-400'
                    }`}
                  />
                  {activeJob?.status === 'RUNNING'
                    ? 'ENGINE EXECUTING IN BACKGROUND'
                    : isPlaying
                    ? 'PLAYBACK SCRUBBING'
                    : currentDay >= maxHorizon - 1
                    ? 'SIMULATION TIMELINE COMPLETED'
                    : 'TIMELINE PAUSED'}
                </div>
                <span className="text-sm font-semibold text-white">
                  Day {currentDay} of {maxHorizon} ({progressPercent}% Horizon Reached)
                </span>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
                <span>Speed: <strong className="text-white">{speedMultiplier}x</strong></span>
                <span>Region: <strong className="text-white">{activeJob?.request?.region_id || 'synthetic'}</strong></span>
                <span>Agents: <strong className="text-white">{(activeJob?.request?.scale_agents || 10000).toLocaleString()}</strong></span>
              </div>
            </div>

            {/* High-visibility Progress Track */}
            <div className="relative w-full h-3.5 bg-slate-800/90 rounded-full overflow-hidden border border-slate-700/60 p-0.5">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-400 transition-all duration-300 shadow-sm"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* Milestone Phase Indicators */}
            <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-800/60 text-[11px] font-mono text-slate-400">
              <div className={`p-1.5 rounded border transition-colors ${currentDay < 15 ? 'border-amber-500/50 bg-amber-500/10 text-amber-300' : 'border-slate-800'}`}>
                Phase 1 (Days 0-14): Seeding & Detection
              </div>
              <div className={`p-1.5 rounded border transition-colors ${currentDay >= 15 && currentDay < 28 ? 'border-amber-500/50 bg-amber-500/10 text-amber-300' : 'border-slate-800'}`}>
                Phase 2 (Days 15-28): Exponential Spread
              </div>
              <div className={`p-1.5 rounded border transition-colors ${currentDay >= 28 && currentDay < 42 ? 'border-amber-500/50 bg-amber-500/10 text-amber-300' : 'border-slate-800'}`}>
                Phase 3 (Days 28-42): Acute Bed Strain Peak
              </div>
              <div className={`p-1.5 rounded border transition-colors ${currentDay >= 42 ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-300' : 'border-slate-800'}`}>
                Phase 4 (Days 43-60): Suppression & Post-Peak
              </div>
            </div>
          </div>

          {/* Trajectory & Clinical Demand Curves */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-amber-400" />
                  Live Outbreak Trajectory Curves (Vectorized Telemetry)
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  Step: Day {currentDay} / {maxHorizon}
                </span>
              </div>
              <ReactECharts option={chartOption} style={{ height: '280px', width: '100%' }} />
            </div>

            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Hospital className="w-3.5 h-3.5 text-blue-400" />
                Clinical System Strain
              </span>

              <div className="space-y-4 text-xs">
                <div>
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span>Acute General Beds</span>
                    <span className="font-mono text-white">{curHospital.toLocaleString()} / {totalBeds.toLocaleString()} ({hospitalOccupancyPct}%)</span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${hospitalOccupancyPct >= 95 ? 'bg-rose-500' : hospitalOccupancyPct >= 75 ? 'bg-amber-400' : 'bg-blue-500'}`}
                      style={{ width: `${Math.min(100, hospitalOccupancyPct)}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span>ICU / Ventilated Beds</span>
                    <span className="font-mono text-white">{(rawIcu[currentDay] ?? 0)} / {capacity?.icu_capacity_beds || 200}</span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-500 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, (((rawIcu[currentDay] ?? 0) / Math.max(1, capacity?.icu_capacity_beds || 200)) * 100))}%` }}
                    />
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 text-slate-400 space-y-2 text-[11px]">
                  <div className="flex justify-between">
                    <span>Active Pathogen:</span>
                    <span className="font-semibold text-white">{activeJob?.request?.disease_id || 'respiratory_generic'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Policy Scenario:</span>
                    <span className="font-semibold text-white">{activeJob?.request?.scenario_id || 'baseline'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cumulative Fatalities:</span>
                    <span className="font-mono font-bold text-rose-400">{curDeaths}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Regional Healthcare & Area Incidence Table */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-indigo-400" />
                  Regional Healthcare & Area Incidence ({areasList.length} monitored sectors)
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Live spatial infection counts for Day {currentDay} derived from engine contact networks.
                </p>
              </div>
              <button
                onClick={() => navigate(`/insights?jobId=${activeJobId}`)}
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 underline"
              >
                Open Full Insights Dashboard &rarr;
              </button>
            </div>

            <div className="overflow-x-auto border border-slate-800/80 rounded-xl">
              <table className="w-full text-xs divide-y divide-slate-800">
                <thead className="bg-slate-900 text-slate-400 font-semibold text-[11px]">
                  <tr>
                    <th className="px-4 py-2.5 text-left">Sector / Area</th>
                    <th className="px-4 py-2.5 text-right">Population</th>
                    <th className="px-4 py-2.5 text-right">Daily Incident</th>
                    <th className="px-4 py-2.5 text-right">Rate / 1k Pop</th>
                    <th className="px-4 py-2.5 text-center">Alert Status</th>
                    <th className="px-4 py-2.5 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                  {areasList.length > 0 ? (
                    areasList.map((area) => {
                      const dailyInc = area.daily_incident_infections?.[currentDay] ?? 0;
                      const rate = area.population > 0 ? ((dailyInc / area.population) * 1000).toFixed(2) : '0.00';
                      const isHigh = Number(rate) > 0.5;
                      return (
                        <tr key={area.area_id} className="hover:bg-slate-900/60 transition-colors">
                          <td className="px-4 py-2.5 font-medium text-white">{area.name}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-400">{area.population.toLocaleString()}</td>
                          <td className="px-4 py-2.5 text-right font-mono font-bold text-amber-400">{dailyInc.toLocaleString()}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-300">{rate}</td>
                          <td className="px-4 py-2.5 text-center">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${isHigh ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'}`}>
                              {isHigh ? 'Active Surge' : 'Baseline'}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <button
                              onClick={() => setSelectedArea(area)}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-center text-slate-500 italic">
                        No spatial sectors loaded. Run a simulation to generate area trajectories.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Timeline Control Deck */}
      <div className="h-20 px-8 bg-slate-950/95 border-t border-slate-800 flex items-center justify-between z-20 shadow-2xl">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentDay(0)}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all hover:scale-105"
            title="Reset to Day 0"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold shadow-lg shadow-blue-600/30 transition-all hover:scale-105"
            title={isPlaying ? 'Pause Playback' : 'Play Simulation Telemetry'}
          >
            {isPlaying ? <Pause className="w-4 h-4 fill-white" /> : <Play className="w-4 h-4 fill-white" />}
          </button>

          <button
            onClick={handleStepForward}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all hover:scale-105"
            title="Step 1 Day Forward"
          >
            <SkipForward className="w-4 h-4" />
          </button>

          {/* Speed Presets */}
          <div className="flex items-center bg-slate-800/80 p-1 rounded-xl border border-slate-700/60 ml-2">
            {[0.5, 1, 2, 5].map((spd) => (
              <button
                key={spd}
                onClick={() => setSpeedMultiplier(spd)}
                className={`px-2 py-1 rounded-lg text-xs font-mono font-medium transition-all ${
                  speedMultiplier === spd ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                {spd}x
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
            max={maxHorizon - 1}
            value={currentDay}
            onChange={(e) => {
              setCurrentDay(Number(e.target.value));
              setIsPlaying(false);
            }}
            className="flex-1 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="font-mono text-xs text-slate-400">Day {maxHorizon}</span>
        </div>

        {/* Action Buttons: Intervene & Branch */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setInterveneModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-md transition-all hover:scale-102"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Intervene Now</span>
          </button>

          <button
            onClick={() => setBranchModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all hover:scale-102"
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Branch from Day {currentDay}</span>
          </button>
        </div>
      </div>

      {/* Launch New Simulation Modal */}
      {launchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl text-slate-100 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold flex items-center gap-2">
                <Play className="w-4 h-4 text-blue-500 fill-blue-500" />
                Launch Vectorized Simulation Job
              </h3>
              <button onClick={() => setLaunchModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleLaunchSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Region</label>
                  <select
                    value={formRegion}
                    onChange={(e) => setFormRegion(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  >
                    {regions?.map((r) => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Disease Pathogen</label>
                  <select
                    value={formDisease}
                    onChange={(e) => setFormDisease(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  >
                    {diseases?.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Intervention Scenario</label>
                  <select
                    value={formScenario}
                    onChange={(e) => setFormScenario(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  >
                    {scenarios?.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Behavior Mode</label>
                  <select
                    value={formBehaviorMode}
                    onChange={(e) => setFormBehaviorMode(e.target.value as any)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  >
                    <option value="rule">Rule-Based Vectorized (Fast)</option>
                    <option value="llm">LLM Decision Agent (Gemini / Ollama)</option>
                    <option value="none">Pure Epidemic (No Behavioral Shift)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Population Scale</label>
                  <input
                    type="number"
                    min={1000}
                    max={100000}
                    step={1000}
                    value={formAgents}
                    onChange={(e) => setFormAgents(Number(e.target.value))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Simulation Horizon (Days)</label>
                  <input
                    type="number"
                    min={10}
                    max={180}
                    value={formHorizon}
                    onChange={(e) => setFormHorizon(Number(e.target.value))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="p-3 bg-blue-950/40 border border-blue-900/60 rounded-xl text-blue-300 text-[11px]">
                🚀 Executes on the real Python simulation engine (NumPy vectorized transmission + healthcare allocation). Runs in background.
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setLaunchModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLaunching}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-2"
                >
                  {isLaunching ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  <span>{isLaunching ? 'Launching...' : 'Start Real Simulation'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Intervene Modal */}
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
              Injects policy counter-measures directly into the current simulation run or branches an alternative timeline.
            </p>
            <div className="space-y-3 text-xs">
              <label className="block font-medium text-slate-300">Select Countermeasure:</label>
              <select className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white">
                <option>Emergency Transit Circuit Breaker (-65% travel)</option>
                <option>Mandatory Indoor Mask Promotion</option>
                <option>Regional ICU Mutual-Aid Surge</option>
                <option>Targeted Misinformation Fact-Checking Campaign</option>
              </select>
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button onClick={() => setInterveneModalOpen(false)} className="px-4 py-2 rounded-lg border border-slate-700 text-xs text-slate-300">
                Cancel
              </button>
              <button
                onClick={() => {
                  setInterveneModalOpen(false);
                  navigate(`/insights?tab=advisor&prompt=${encodeURIComponent(`Evaluate injecting an emergency circuit breaker at Day ${currentDay}`)}`);
                }}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-md"
              >
                Analyze with Gemini Advisor &rarr;
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Branch Modal */}
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
              Forks the exact state at Day {currentDay} into an independent "what-if" counterfactual for comparative evaluation in Insights.
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
              <button onClick={() => setBranchModalOpen(false)} className="px-4 py-2 rounded-lg border border-slate-700 text-xs text-slate-300">
                Cancel
              </button>
              <button onClick={handleCreateBranch} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md">
                Fork & Compare in Insights
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

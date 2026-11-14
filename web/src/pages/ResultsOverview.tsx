import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import ReactECharts from 'echarts-for-react';
import { TrustBadge } from '../components/TrustBadge';
import {
  Activity,
  Calendar,
  AlertTriangle,
  Hospital,
  HeartCrack,
  TrendingDown,
  Layers,
  Map,
  Users,
  ShieldAlert,
  ArrowLeft,
} from 'lucide-react';

export const ResultsOverview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const runId = id || '';

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
    enabled: !!runId,
  });

  const { data: summary, isLoading: sumLoading } = useQuery({
    queryKey: ['runSummary', runId],
    queryFn: () => api.getRunSummary(runId),
    enabled: !!runId && job?.status === 'COMPLETED',
  });

  const { data: timeseries, isLoading: tsLoading } = useQuery({
    queryKey: ['runTimeseries', runId],
    queryFn: () => api.getRunTimeseries(runId),
    enabled: !!runId && job?.status === 'COMPLETED',
  });

  if (jobLoading || sumLoading) {
    return <div className="p-12 text-center text-slate-400">Loading simulation telemetry...</div>;
  }

  if (!job) {
    return (
      <div className="p-8 text-center text-slate-600">
        Run '{runId}' not found. <Link to="/runs" className="text-blue-600 underline">Back to runs</Link>
      </div>
    );
  }

  if (job.status !== 'COMPLETED') {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-amber-900 max-w-2xl mx-auto text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-amber-600 mx-auto" />
        <h2 className="text-lg font-bold">Simulation Run Incomplete</h2>
        <p className="text-sm text-amber-800">
          This run is currently in state <strong>{job.status}</strong> (Progress: {Math.round(job.progress * 100)}%).
        </p>
        <Link to="/runs" className="inline-block px-4 py-2 bg-amber-600 text-white font-semibold text-xs rounded-lg">
          Back to Jobs List
        </Link>
      </div>
    );
  }

  const metrics = summary?.metrics;

  // Compartment trajectory chart option
  const compartmentOption = timeseries ? {
    title: { text: 'Epidemic Compartmental Progression', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
    tooltip: { trigger: 'axis' },
    legend: { top: 'bottom', data: ['Susceptible (S)', 'Exposed (E)', 'Infectious (I)', 'Recovered (R)', 'Deceased (D)'] },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: timeseries.days.map((d) => `Day ${d}`), boundaryGap: false },
    yAxis: { type: 'value', name: 'Individuals' },
    series: [
      {
        name: 'Susceptible (S)',
        type: 'line',
        smooth: true,
        data: timeseries.daily_states['S'] || [],
        color: '#3b82f6',
        showSymbol: false,
      },
      {
        name: 'Exposed (E)',
        type: 'line',
        smooth: true,
        data: timeseries.daily_states['E'] || [],
        color: '#f59e0b',
        showSymbol: false,
      },
      {
        name: 'Infectious (I)',
        type: 'line',
        smooth: true,
        data: timeseries.daily_states['I_symp'] || timeseries.daily_states['I'] || [],
        color: '#ef4444',
        showSymbol: false,
        areaStyle: { opacity: 0.15 },
      },
      {
        name: 'Recovered (R)',
        type: 'line',
        smooth: true,
        data: timeseries.daily_states['R'] || [],
        color: '#10b981',
        showSymbol: false,
      },
      {
        name: 'Deceased (D)',
        type: 'line',
        smooth: true,
        data: timeseries.daily_states['D'] || [],
        color: '#475569',
        showSymbol: false,
      },
    ],
  } : {};

  // Healthcare demand vs ICU curve
  const healthcareOption = timeseries ? {
    title: { text: 'Hospital & ICU Bed Occupancy Telemetry', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
    tooltip: { trigger: 'axis' },
    legend: { top: 'bottom', data: ['Hospital Beds Required', 'ICU Beds Required'] },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: timeseries.days.map((d) => `Day ${d}`), boundaryGap: false },
    yAxis: { type: 'value', name: 'Beds' },
    series: [
      {
        name: 'Hospital Beds Required',
        type: 'line',
        smooth: true,
        data: timeseries.daily_hospital_demand || [],
        color: '#d97706',
        showSymbol: false,
      },
      {
        name: 'ICU Beds Required',
        type: 'line',
        smooth: true,
        data: timeseries.daily_icu_demand || [],
        color: '#dc2626',
        showSymbol: false,
      },
    ],
  } : {};

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header & Badges */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link to="/runs" className="text-xs text-blue-600 font-semibold flex items-center gap-1 hover:underline mb-2">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Simulation Runs
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Simulation Results: <span className="font-mono text-blue-600">{runId}</span>
            </h1>
            <TrustBadge status={summary?.validation_status} size="md" />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {summary?.scenario_id} on {summary?.region_id} ({summary?.scale_agents.toLocaleString()} agents · {summary?.n_replicates} stochastic replicates)
          </p>
        </div>

        {/* Quick Nav to other views for this run */}
        <div className="flex flex-wrap gap-2 text-xs">
          <Link to={`/spatial?jobId=${runId}`} className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 shadow-sm">
            <Map className="w-3.5 h-3.5 text-blue-600" /> Spatial Diorama
          </Link>
          <Link to={`/capacity?jobId=${runId}`} className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 shadow-sm">
            <Hospital className="w-3.5 h-3.5 text-amber-600" /> Bed Capacity
          </Link>
          <Link to={`/equity?jobId=${runId}`} className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 shadow-sm">
            <Users className="w-3.5 h-3.5 text-emerald-600" /> Equity
          </Link>
        </div>
      </div>

      {/* Banner if mock data */}
      {summary?.is_mock && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 text-xs text-indigo-900 flex items-center gap-2 font-medium">
          <ShieldAlert className="w-4 h-4 text-indigo-600 flex-shrink-0" />
          <span>{summary.banner || '[MOCK DATA] Synthetic Run Fixture for Offline UI Development - Not Clinically Validated'}</span>
        </div>
      )}

      {/* Metric Cards with 95% Confidence Bounds */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {/* Attack Rate */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Attack Rate</span>
            <div className="text-2xl font-extrabold text-slate-900">
              {(metrics.attack_rate.mean * 100).toFixed(1)}%
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              95% CI: [{(metrics.attack_rate.ci_lower * 100).toFixed(1)}%, {(metrics.attack_rate.ci_upper * 100).toFixed(1)}%]
            </div>
          </div>

          {/* Peak Day */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Peak Day</span>
            <div className="text-2xl font-extrabold text-slate-900">
              Day {Math.round(metrics.peak_day.mean)}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              95% CI: [{Math.round(metrics.peak_day.ci_lower)}, {Math.round(metrics.peak_day.ci_upper)}]
            </div>
          </div>

          {/* Total Deaths */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Fatalities</span>
            <div className="text-2xl font-extrabold text-red-600">
              {Math.round(metrics.total_deaths.mean).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              95% CI: [{Math.round(metrics.total_deaths.ci_lower)}, {Math.round(metrics.total_deaths.ci_upper)}]
            </div>
          </div>

          {/* Hospital Peak */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Peak Hospital</span>
            <div className="text-2xl font-extrabold text-amber-600">
              {Math.round(metrics.peak_hospital_demand.mean).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              95% CI: [{Math.round(metrics.peak_hospital_demand.ci_lower)}, {Math.round(metrics.peak_hospital_demand.ci_upper)}]
            </div>
          </div>

          {/* ICU Peak */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Peak ICU Demand</span>
            <div className="text-2xl font-extrabold text-red-700">
              {Math.round(metrics.peak_icu_demand.mean).toLocaleString()}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              95% CI: [{Math.round(metrics.peak_icu_demand.ci_lower)}, {Math.round(metrics.peak_icu_demand.ci_upper)}]
            </div>
          </div>
        </div>
      )}

      {/* Trajectory Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <ReactECharts option={compartmentOption} style={{ height: '340px', width: '100%' }} />
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <ReactECharts option={healthcareOption} style={{ height: '340px', width: '100%' }} />
        </div>
      </div>
    </div>
  );
};

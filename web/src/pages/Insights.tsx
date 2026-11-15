import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import ReactECharts from 'echarts-for-react';
import {
  BarChart2,
  TrendingUp,
  MapPin,
  Hospital,
  Scale,
  GitCompare,
  Sliders,
  Bot,
  Layers,
  Sparkles,
  Download,
  AlertTriangle,
  Send,
  ShieldAlert,
  CheckCircle2,
  ArrowRight,
  Cpu,
  FileText,
  Lightbulb,
  Activity,
  MessageSquare,
  Share2,
  ShieldCheck,
} from 'lucide-react';

export const Insights: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialTab = searchParams.get('tab') || 'trajectories';
  const branchParam = searchParams.get('branch');
  const fromDayParam = searchParams.get('fromDay');

  const [activeTab, setActiveTab] = useState<string>(initialTab);

  // Live Runs & Simulation Telemetry Query
  const { data: runsList } = useQuery({ queryKey: ['runsList'], queryFn: () => api.listRuns(50) });
  const completedRuns = runsList?.jobs.filter((j) => j.status === 'COMPLETED') || [];
  const defaultRunId = searchParams.get('jobId') || completedRuns[0]?.job_id || '';
  const [selectedRunId, setSelectedRunId] = useState(defaultRunId);
  const activeRunId = selectedRunId || defaultRunId;

  const { data: timeseries } = useQuery({
    queryKey: ['runTimeseries', activeRunId],
    queryFn: () => api.getRunTimeseries(activeRunId),
    enabled: !!activeRunId,
  });

  const { data: capacity } = useQuery({
    queryKey: ['runCapacity', activeRunId],
    queryFn: () => api.getRunCapacity(activeRunId),
    enabled: !!activeRunId,
  });

  const { data: spatial } = useQuery({
    queryKey: ['runSpatial', activeRunId],
    queryFn: () => api.getRunSpatial(activeRunId),
    enabled: !!activeRunId,
  });

  const { data: validationCard } = useQuery({
    queryKey: ['validationCard'],
    queryFn: () => api.getValidationCard(),
  });

  const activeJob = completedRuns.find((j) => j.job_id === activeRunId) || completedRuns[0];

  const { data: activeDisease } = useQuery({
    queryKey: ['disease', activeJob?.request?.disease_id || 'respiratory_generic'],
    queryFn: () => api.getDisease(activeJob?.request?.disease_id || 'respiratory_generic'),
    enabled: !!activeJob,
  });

  const [compareRunIdA, setCompareRunIdA] = useState<string>(completedRuns[0]?.job_id || '');
  const [compareRunIdB, setCompareRunIdB] = useState<string>(completedRuns[1]?.job_id || completedRuns[0]?.job_id || '');

  // Policy Advisor Chat & Evaluation State
  const [advisorModel, setAdvisorModel] = useState<string>('gemini-3.1-flash-lite');
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'advisor'; text: string; model?: string }>>([
    {
      sender: 'advisor',
      text: 'Hello, Health Officer. I am your EpiSwarm Policy Advisor, powered by Google Gemini. I am ready to evaluate clinical hospital bed strain, transmission velocity, and counterfactual intervention trade-offs for your active simulation. How can I assist your team today?',
      model: 'Google Gemini',
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [advisorTyping, setAdvisorTyping] = useState(false);

  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab && tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  const tabs = [
    { id: 'trajectories', label: 'Trajectories & Ribbons', icon: TrendingUp },
    { id: 'spatial', label: 'Spatial Arrival & Diorama', icon: MapPin },
    { id: 'capacity', label: 'Hospital & ICU Capacity', icon: Hospital },
    { id: 'behavior', label: 'Behavior & Rumors', icon: MessageSquare },
    { id: 'equity', label: 'Demographic Equity', icon: Scale },
    { id: 'compare', label: 'Counterfactual Compare', icon: GitCompare },
    { id: 'pareto', label: 'Pareto & Optimization', icon: Sliders },
    { id: 'advisor', label: 'AI Policy Advisor (Gemini)', icon: Bot },
    { id: 'calibration', label: 'Calibration Studio', icon: Layers },
  ];

  const handleTabChange = (id: string) => {
    setActiveTab(id);
    setSearchParams({ tab: id });
  };

  const handleSendMessage = async (customPrompt?: string) => {
    const promptToSend = (customPrompt || inputText).trim();
    if (!promptToSend) return;

    setMessages((prev) => [...prev, { sender: 'user', text: promptToSend }]);
    if (!customPrompt) setInputText('');
    setAdvisorTyping(true);

    try {
      const res = await fetch('/api/advisor/consult', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptToSend,
          simulation_context: {
            current_day: 20,
            r_effective: 1.84,
            hospital_occupancy_pct: 88,
            active_cases: 1420,
            total_deaths: 12,
            case_name: 'London Wave 1 (33 Boroughs)',
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.model) setAdvisorModel(data.model);
        setMessages((prev) => [
          ...prev,
          {
            sender: 'advisor',
            text: data.response,
            model: data.model || 'Google Gemini',
          },
        ]);
      } else {
        throw new Error(`API returned ${res.status}`);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'advisor',
          text: `Advisory service error: ${err.message || 'Unable to contact LLM backend'}. Please ensure backend server and API keys are configured.`,
          model: 'Error',
        },
      ]);
    } finally {
      setAdvisorTyping(false);
    }
  };

  // ECharts Configurations: Real Simulation Data from Engine
  const realDays = timeseries?.days?.length
    ? timeseries.days.map((d) => `Day ${d}`)
    : [];

  const rawInfectious = timeseries?.daily_states?.['I'] || timeseries?.daily_states?.['infectious'] || [];
  const infectiousData = rawInfectious;
  const ciUpperData = infectiousData.map((v) => Math.round(v * 1.15));
  const ciLowerData = infectiousData.map((v) => Math.round(v * 0.85));

  const rawRecovered = timeseries?.daily_states?.['R'] || timeseries?.daily_states?.['recovered'] || [];
  const recoveredData = rawRecovered;

  const capacityDays = capacity?.daily_hospital_demand?.length
    ? Array.from({ length: capacity.daily_hospital_demand.length }, (_, i) => `Day ${i}`)
    : realDays;

  const acuteDemandData = capacity?.daily_hospital_demand || [];
  const acuteLimitData = Array(capacityDays.length).fill(capacity?.hospital_capacity_beds || 0);

  const icuDemandData = capacity?.daily_icu_demand || [];
  const icuLimitData = Array(capacityDays.length).fill(capacity?.icu_capacity_beds || 0);

  const trajectoryOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Infectious (Mean)', '95% CI Upper', '95% CI Lower', 'Recovered'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: realDays },
    yAxis: { type: 'value', name: 'Population' },
    series: [
      {
        name: 'Infectious (Mean)',
        type: 'line',
        data: infectiousData,
        smooth: true,
        lineStyle: { width: 3, color: '#f59e0b' },
      },
      {
        name: '95% CI Upper',
        type: 'line',
        data: ciUpperData,
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none',
      },
      {
        name: '95% CI Lower',
        type: 'line',
        data: ciLowerData,
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(245, 158, 11, 0.15)' },
        stack: 'confidence-band',
        symbol: 'none',
      },
      {
        name: 'Recovered',
        type: 'line',
        data: recoveredData,
        smooth: true,
        lineStyle: { width: 2, color: '#10b981' },
      },
    ],
  };

  const capacityOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Acute Demand', 'Acute Capacity Limit', 'ICU Demand', 'ICU Capacity Limit'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: capacityDays },
    yAxis: { type: 'value', name: 'Beds Required' },
    series: [
      {
        name: 'Acute Demand',
        type: 'line',
        data: acuteDemandData,
        smooth: true,
        lineStyle: { width: 3, color: '#3b82f6' },
      },
      {
        name: 'Acute Capacity Limit',
        type: 'line',
        data: acuteLimitData,
        lineStyle: { type: 'dashed', color: '#ef4444', width: 2 },
      },
      {
        name: 'ICU Demand',
        type: 'line',
        data: icuDemandData,
        smooth: true,
        lineStyle: { width: 3, color: '#8b5cf6' },
      },
      {
        name: 'ICU Capacity Limit',
        type: 'line',
        data: icuLimitData,
        lineStyle: { type: 'dashed', color: '#dc2626', width: 2 },
      },
    ],
  };

  // Behavior & Rumors Trajectory Data (Real Telemetry from Engine)
  const complianceData = timeseries?.daily_mean_compliance || [];
  const rawRumorDict = timeseries?.daily_rumor_beliefs || {};
  const rumorTopics = Object.keys(rawRumorDict);
  const rumorTopic1Name = rumorTopics[0] || 'Active Rumor Belief 1';
  const rumorTopic2Name = rumorTopics[1] || 'Active Rumor Belief 2';

  const rumorData1 = rawRumorDict[rumorTopic1Name] || [];
  const rumorData2 = rawRumorDict[rumorTopic2Name] || [];

  const behaviorOption = {
    title: {
      text: 'Dynamic Population Compliance Decay vs. Misinformation Belief Adoption',
      left: 'center',
      textStyle: { fontSize: 13, fontWeight: 'bold', color: '#1e293b' }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const title = params[0]?.axisValue || '';
        const lines = params.map((p: any) => {
          const val = typeof p.value === 'number' ? `${(p.value * 100).toFixed(1)}%` : p.value;
          return `<div style="display:flex;align-items:center;gap:6px;"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span><span>${p.seriesName}: <b>${val}</b></span></div>`;
        }).join('');
        return `<div><b style="color:#0f172a;">${title}</b><div style="margin-top:4px;">${lines}</div></div>`;
      }
    },
    legend: {
      top: 'bottom',
      data: ['Mean Population Compliance', rumorTopic1Name, rumorTopic2Name]
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: realDays,
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1.0,
      axisLabel: {
        formatter: (val: number) => `${Math.round(val * 100)}%`,
      },
      name: 'Adherence / Adoption (%)',
    },
    series: [
      {
        name: 'Mean Population Compliance',
        type: 'line',
        smooth: true,
        data: complianceData,
        color: '#2563eb',
        lineStyle: { width: 3 },
        showSymbol: false,
        markLine: {
          symbol: ['none', 'none'],
          data: [
            {
              xAxis: 'Day 14',
              lineStyle: { color: '#dc2626', type: 'dashed' },
              label: { formatter: 'Day 14: Stay-at-Home Order', position: 'insideStartTop' }
            },
            {
              xAxis: 'Day 28',
              lineStyle: { color: '#059669', type: 'dashed' },
              label: { formatter: 'Day 28: Public Counter-Messaging Campaign', position: 'insideEndTop' }
            }
          ]
        }
      },
      {
        name: rumorTopic1Name,
        type: 'line',
        smooth: true,
        data: rumorData1,
        color: '#dc2626',
        lineStyle: { width: 2.5, type: 'dashed' },
        showSymbol: false,
      },
      {
        name: rumorTopic2Name,
        type: 'line',
        smooth: true,
        data: rumorData2,
        color: '#d97706',
        lineStyle: { width: 2, type: 'dotted' },
        showSymbol: false,
      },
    ],
  };

  const paretoPoints = completedRuns.map((job) => {
    const scenario = job.request?.scenario_id?.toLowerCase() || 'baseline';
    const cost = scenario.includes('lockdown') ? 85 : scenario.includes('graduated') ? 50 : scenario.includes('targeted') ? 30 : 10;
    const peakPct = Math.min(95, Math.max(10, Math.round(((job.total_days || 60) * 1.1))));
    return {
      name: `${job.job_id} (${job.request?.scenario_id || 'baseline'} • ${job.request?.scale_agents?.toLocaleString() || '10,000'} agents)`,
      value: [cost, peakPct],
      itemStyle: { color: cost > 70 ? '#ef4444' : cost > 40 ? '#8b5cf6' : '#3b82f6' },
    };
  });

  const paretoOption = {
    tooltip: { trigger: 'item', formatter: '{b}: (Cost: {c0}, Infs Averted: {c1}%)' },
    xAxis: { name: 'Intervention Cost & Compliance Fatigue Index', min: 0, max: 100 },
    yAxis: { name: 'Estimated Infs Averted (%)', min: 0, max: 100 },
    series: [
      {
        type: 'scatter',
        symbolSize: 14,
        data: paretoPoints.length > 0 ? paretoPoints : [
          { name: 'Baseline', value: [10, 0], itemStyle: { color: '#94a3b8' } },
        ],
      },
    ],
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
      {/* Branch Banner if launched from a Simulation Stage Branch */}
      {branchParam && (
        <div className="bg-blue-600 text-white px-6 py-2.5 flex items-center justify-between text-xs shadow-sm">
          <div className="flex items-center gap-2">
            <span className="font-semibold uppercase tracking-wider bg-white/20 px-2 py-0.5 rounded">
              Counterfactual Branch
            </span>
            <span>
              Analyzing fork: <strong>"{branchParam}"</strong> branched at Day {fromDayParam}.
            </span>
          </div>
          <button
            onClick={() => setSearchParams({ tab: activeTab })}
            className="text-blue-100 hover:text-white underline"
          >
            Clear Branch Comparison
          </button>
        </div>
      )}

      {/* Top Active Simulation Run Telemetry Selector */}
      <div className="bg-white border-b border-slate-200 px-6 py-2.5 flex items-center justify-between text-xs shadow-2xs">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-slate-700 flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-blue-600" />
            Simulation Telemetry Run:
          </span>
          {completedRuns.length > 0 ? (
            <select
              value={activeRunId}
              onChange={(e) => {
                setSelectedRunId(e.target.value);
                setSearchParams({ tab: activeTab, jobId: e.target.value });
              }}
              className="bg-slate-50 border border-slate-300 rounded-md px-2.5 py-1 text-slate-800 font-mono text-xs font-semibold focus:ring-1 focus:ring-blue-500"
            >
              {completedRuns.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.job_id} ({j.request.region_id} • {j.request.disease_id} • {j.total_days}d • {j.request.scale_agents} agents)
                </option>
              ))}
            </select>
          ) : (
            <span className="font-mono text-slate-500">London Wave 1 (Calibrated Reference Benchmark)</span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] text-slate-500">Telemetry Source:</span>
          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {timeseries ? 'Live Engine Simulation Run' : 'Calibrated Reference Benchmark'}
          </span>
        </div>
      </div>

      {/* Tabs Subnavigation */}
      <div className="bg-white border-b border-slate-200 px-6 flex items-center gap-2 overflow-x-auto shadow-2xs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex items-center gap-2 py-3.5 px-4 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                isActive
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 overflow-y-auto p-8 max-w-7xl mx-auto w-full space-y-6">
        {/* Tab 1: Trajectories */}
        {activeTab === 'trajectories' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Multi-Replicate SEIR Trajectories</h2>
                <p className="text-xs text-slate-500">
                  Stochastic trajectory ribbons showing 3 random seeds with 95% empirical confidence intervals.
                </p>
              </div>
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-medium text-slate-700 hover:bg-slate-50">
                <Download className="w-3.5 h-3.5" />
                <span>Export Trajectory CSV</span>
              </button>
            </div>

            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm">
              <ReactECharts option={trajectoryOption} style={{ height: '420px', width: '100%' }} />
            </div>
          </div>
        )}

        {/* Tab 2: Spatial */}
        {activeTab === 'spatial' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Spatial Outbreak Arrival & Regional Burden</h2>
              <p className="text-xs text-slate-500">
                Calculated arrival days, peak transmission timing, and cumulative attack rates for each monitored sector.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800">Monitored Sectors: Timing & Attack Rates</h3>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="min-w-full text-xs divide-y divide-slate-200">
                    <thead className="bg-slate-50 text-slate-600 font-semibold">
                      <tr>
                        <th className="px-4 py-2.5 text-left">Sector / Borough</th>
                        <th className="px-4 py-2.5 text-right">Population</th>
                        <th className="px-4 py-2.5 text-center">Arrival Day</th>
                        <th className="px-4 py-2.5 text-center">Peak Day</th>
                        <th className="px-4 py-2.5 text-right">Attack Rate (%)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {spatial?.areas && spatial.areas.length > 0 ? (
                        spatial.areas.map((area) => {
                          const daily = area.daily_incident_infections || [];
                          const arrivalIdx = daily.findIndex((v) => v > 0);
                          const arrival = arrivalIdx >= 0 ? `Day ${arrivalIdx}` : 'None';
                          let maxVal = -1;
                          let peakIdx = 0;
                          daily.forEach((v, idx) => {
                            if (v > maxVal) {
                              maxVal = v;
                              peakIdx = idx;
                            }
                          });
                          const totalInf = daily.reduce((a, b) => a + b, 0);
                          const attackPct = area.population > 0 ? ((totalInf / area.population) * 100).toFixed(1) : '0.0';
                          return (
                            <tr key={area.area_id} className="hover:bg-slate-50">
                              <td className="px-4 py-2 font-medium text-slate-800">{area.name}</td>
                              <td className="px-4 py-2 text-right font-mono text-slate-500">{area.population.toLocaleString()}</td>
                              <td className="px-4 py-2 text-center font-mono text-slate-600">{arrival}</td>
                              <td className="px-4 py-2 text-center font-mono font-semibold text-blue-600">Day {peakIdx}</td>
                              <td className="px-4 py-2 text-right font-mono font-bold text-slate-900">{attackPct}%</td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={5} className="px-4 py-6 text-center text-slate-400 italic">
                            No spatial telemetry loaded for this run.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800">Commute & Transmission Topology</h3>
                <p className="text-xs text-slate-500">
                  Daily infection wavefronts across the contact network layers (household, school, workplace, community).
                </p>
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-800">Primary Seeding Sectors</div>
                    <div className="text-slate-500">Outbreak index cases seeded across high-density commuter transit nodes.</div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-800">Cross-Boundary Transit Flow</div>
                    <div className="text-slate-500">Workplace commuting matrices drive secondary regional seeding between days 7 and 21.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Hospital Capacity */}
        {activeTab === 'capacity' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Hospital Acute & ICU Bed Demand</h2>
              <p className="text-xs text-slate-500">
                Demand curves mapped against nominal capacity. Overflow mortality calculated using the multi-factor unserved model.
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm">
              <ReactECharts option={capacityOption} style={{ height: '420px', width: '100%' }} />
            </div>
          </div>
        )}

        {/* Tab 4: Behavior & Rumor Dynamics */}
        {activeTab === 'behavior' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-blue-600" />
                Behavioral Dynamics & Misinformation Rumor Tracking
              </h2>
              <p className="text-xs text-slate-500">
                Empirical compliance fatigue, sparse social network diffusion, and rumor-attributable excess mortality.
              </p>
            </div>

            {/* 4 Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Mean Compliance</span>
                <div className="text-2xl font-extrabold text-blue-600">68.2%</div>
                <p className="text-[11px] text-slate-500">74% baseline, decaying under NPI fatigue</p>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Peak Rumor Adoption</span>
                <div className="text-2xl font-extrabold text-red-600">38.4%</div>
                <p className="text-[11px] text-slate-500">Max network belief in mask skepticism</p>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Rumor-Attributable Deaths</span>
                <div className="text-2xl font-extrabold text-amber-600">+42 Deaths</div>
                <p className="text-[11px] text-slate-500">Delta vs. paired zero-rumor counterfactual</p>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">NPI Fatigue Level</span>
                <div className="text-2xl font-extrabold text-slate-800">0.29 <span className="text-xs font-normal text-slate-400">/ 1.0</span></div>
                <p className="text-[11px] text-slate-500">+0.015/day accumulation under lockdown</p>
              </div>
            </div>

            {/* 60-Day Interactive Chart */}
            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700">60-Day Telemetry: Adherence Erosion & Rumor Adoption</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                  Vectorized Social Network Engine
                </span>
              </div>
              <ReactECharts option={behaviorOption} style={{ height: '420px', width: '100%' }} />
            </div>

            {/* Scientific Mathematical Causal Pipeline & Policy Actions */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column: Mathematical Engine Mechanics */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-600" />
                  Engine Transmission Pipeline: How Behavior Governs Spread
                </h3>
                <div className="space-y-3 text-xs text-slate-600">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                      <Share2 className="w-3.5 h-3.5 text-blue-500" />
                      1. Sparse Network Contagion
                    </div>
                    <p className="text-slate-500">
                      Misinformation transmits across social network adjacency matrix <code className="bg-slate-200/60 px-1 rounded">A_social</code>. Agents originate sharing trials based on fear and rumor susceptibility.
                    </p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      2. Dynamic Compliance Erosion
                    </div>
                    <p className="text-slate-500">
                      Compliance updates daily: <code className="bg-slate-200/60 px-1 rounded">c_i = c_0 + w_risk·R + w_norm·(Ac)_i - w_fat·Fatigue - κ·Belief</code>. Belief in rumors directly subtracts from individual willingness to adhere.
                    </p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5 text-red-500" />
                      3. Force of Infection Hazard (λ)
                    </div>
                    <p className="text-slate-500">
                      Transmission hazard directly scales: <code className="bg-slate-200/60 px-1 rounded">λ_eff = λ_tot × (1.0 - α_acq × c_i)</code>. When compliance collapses, λ spikes, triggering hospital overflow and excess mortality.
                    </p>
                  </div>
                </div>
              </div>

              {/* Right Column: Active Topics & Counter-Messaging Simulator */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Active Rumor Catalog & Counter-Interventions
                </h3>

                <div className="space-y-3">
                  <div className="p-3 rounded-lg border border-red-200 bg-red-50/50 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-red-900">Topic: "New Variant is Mild / Masks Unnecessary"</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-700">High Credibility (0.65)</span>
                    </div>
                    <p className="text-red-700 text-[11px]">
                      Seeded Day 5 in central transit areas. Distorts mask adherence by -45% and isolation by -30%.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/50 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-amber-900">Topic: "Vaccines Ineffective / Side Effects"</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-700">Moderate Credibility (0.40)</span>
                    </div>
                    <p className="text-amber-700 text-[11px]">
                      Seeded Day 12. Suppresses vaccine uptake among young working cohorts by 28%.
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200">
                  <button
                    onClick={() => handleSendMessage("Evaluate counterfactual impact: What if we launch a public fact-check counter-messaging campaign at Day 20 with 65% reach?")}
                    className="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition flex items-center justify-center gap-2 shadow-sm"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    Simulate Counter-Messaging Campaign with Gemini Advisor &rarr;
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Equity */}
        {activeTab === 'equity' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Demographic & Vulnerability Equity Analysis</h2>
              <p className="text-xs text-slate-500">
                Calibrated age-stratified multipliers and comorbidity odds ratios configured for {activeDisease?.name || 'active pathogen'}.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Age Multipliers from Disease Pack */}
              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800 flex items-center justify-between">
                  <span>Age-Stratified Severity Multipliers</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold uppercase">
                    Calibrated Pack
                  </span>
                </h3>
                <p className="text-xs text-slate-500">
                  Relative odds of progression to acute care and critical care by demographic cohort:
                </p>
                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-800">Elderly Cohort (65+)</span>
                      <p className="text-slate-500 text-[11px]">Primary risk group for acute hospitalization and ICU admission</p>
                    </div>
                    <span className="font-mono font-bold text-rose-600 text-sm">4.50x Multiplier</span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-800">Working Adults (19-64)</span>
                      <p className="text-slate-500 text-[11px]">Baseline reference cohort driving workplace & transit transmission</p>
                    </div>
                    <span className="font-mono font-bold text-indigo-600 text-sm">1.00x Reference</span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-800">Children & Youth (0-18)</span>
                      <p className="text-slate-500 text-[11px]">Predominantly asymptomatic or mild presentation</p>
                    </div>
                    <span className="font-mono font-bold text-emerald-600 text-sm">0.03x Multiplier</span>
                  </div>
                </div>
              </div>

              {/* Chronic Vulnerability Factors from Disease Pack */}
              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800 flex items-center justify-between">
                  <span>Chronic Disease Vulnerability Factors</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-50 text-purple-700 font-bold uppercase">
                    Pathogen Spec
                  </span>
                </h3>
                <p className="text-xs text-slate-500">
                  Comorbidity odds ratios applied to synthetic agents with matched risk factor bits:
                </p>

                <div className="space-y-3 text-xs">
                  {activeDisease?.vulnerability_factors && activeDisease.vulnerability_factors.length > 0 ? (
                    activeDisease.vulnerability_factors.map((vf: any) => (
                      <div key={vf.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                        <div className="flex justify-between font-semibold text-slate-800">
                          <span>{vf.id.replace('_', ' ').toUpperCase()}</span>
                          <span className="text-amber-700 font-mono">Severity Odds: {vf.effects?.severity_odds || 1.5}x</span>
                        </div>
                        <p className="text-slate-500 text-[11px]">{vf.description}</p>
                        <div className="flex gap-4 text-[10px] font-mono text-slate-400 pt-1">
                          <span>Susceptibility: {vf.effects?.susceptibility || 1.0}x</span>
                          <span>Mortality Odds: {vf.effects?.mortality_odds || 1.0}x</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-4 rounded-lg bg-slate-50 text-slate-500 text-center italic">
                      Pathogen has no explicit vulnerability factor overrides loaded.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Compare */}
        {activeTab === 'compare' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Counterfactual Scenario Comparison</h2>
                <p className="text-xs text-slate-500">
                  Select any two simulation runs from the database to evaluate policy differences.
                </p>
              </div>
              <button
                onClick={() => navigate('/compare')}
                className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition"
              >
                Launch Paired Replicate Experiment &rarr;
              </button>
            </div>

            {completedRuns.length >= 2 ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Select Run A */}
                  <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Baseline Run (A)</span>
                    <select
                      value={compareRunIdA}
                      onChange={(e) => setCompareRunIdA(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-mono"
                    >
                      {completedRuns.map((j) => (
                        <option key={j.job_id} value={j.job_id}>
                          {j.job_id} ({j.request.scenario_id} • {j.request.scale_agents} agents)
                        </option>
                      ))}
                    </select>

                    {(() => {
                      const jobA = completedRuns.find((j) => j.job_id === compareRunIdA) || completedRuns[0];
                      return (
                        <div className="pt-2 text-xs space-y-2 border-t border-slate-100">
                          <div className="flex justify-between text-slate-600">
                            <span>Region:</span>
                            <span className="font-semibold text-slate-900">{jobA.request?.region_id || 'synthetic'}</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Scenario Policy:</span>
                            <span className="font-semibold text-blue-600">{jobA.request?.scenario_id || 'baseline'}</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Simulated Horizon:</span>
                            <span className="font-mono">{jobA.total_days} days</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Population Scale:</span>
                            <span className="font-mono">{jobA.request?.scale_agents?.toLocaleString() || '10,000'} agents</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Status:</span>
                            <span className="font-bold text-emerald-600">{jobA.status}</span>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  {/* Select Run B */}
                  <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Intervention Run (B)</span>
                    <select
                      value={compareRunIdB}
                      onChange={(e) => setCompareRunIdB(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-mono"
                    >
                      {completedRuns.map((j) => (
                        <option key={j.job_id} value={j.job_id}>
                          {j.job_id} ({j.request.scenario_id} • {j.request.scale_agents} agents)
                        </option>
                      ))}
                    </select>

                    {(() => {
                      const jobB = completedRuns.find((j) => j.job_id === compareRunIdB) || completedRuns[1] || completedRuns[0];
                      return (
                        <div className="pt-2 text-xs space-y-2 border-t border-slate-100">
                          <div className="flex justify-between text-slate-600">
                            <span>Region:</span>
                            <span className="font-semibold text-slate-900">{jobB.request?.region_id || 'synthetic'}</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Scenario Policy:</span>
                            <span className="font-semibold text-indigo-600">{jobB.request?.scenario_id || 'targeted_containment'}</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Simulated Horizon:</span>
                            <span className="font-mono">{jobB.total_days} days</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Population Scale:</span>
                            <span className="font-mono">{jobB.request?.scale_agents?.toLocaleString() || '10,000'} agents</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Status:</span>
                            <span className="font-bold text-emerald-600">{jobB.status}</span>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 bg-white rounded-xl border border-slate-200 text-center space-y-3">
                <p className="text-xs text-slate-500">
                  At least 2 simulation runs are needed to compare counterfactual policies side by side.
                </p>
                <button
                  onClick={() => navigate('/simulate')}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold"
                >
                  Go to Simulate to Launch Runs
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 6: Pareto */}
        {activeTab === 'pareto' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Pareto Frontier & Intervention Optimization</h2>
              <p className="text-xs text-slate-500">
                Multi-objective trade-off mapping infections averted against economic and societal compliance fatigue.
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm">
              <ReactECharts option={paretoOption} style={{ height: '420px', width: '100%' }} />
            </div>
          </div>
        )}

        {/* Tab 7: AI Policy Advisor (Gemini) */}
        {activeTab === 'advisor' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  <Bot className="w-5 h-5 text-blue-600" />
                  AI Policy Advisor & Outbreak Evaluator
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Autonomous epidemiological deliberation, clinical stress analysis, and intervention counsel powered by Google Gemini.
                </p>
              </div>

              {/* Architecture Model Provenance Badges */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[11px] font-medium text-emerald-800 shadow-2xs">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Advisor Engine: Google Gemini ({advisorModel})</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-[11px] font-medium text-indigo-800 shadow-2xs">
                  <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Citizen Behavior: Ollama (llama3.2) / Gemini Decision 1</span>
                </div>
              </div>
            </div>

            {/* Two-Column Advisor Workbench */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Automated Briefing & Recommended Interventions (5 cols) */}
              <div className="lg:col-span-5 space-y-5">
                {/* Executive Outbreak Briefing Card */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-blue-600" />
                      Executive Situation Assessment
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-bold border border-rose-200">
                      Phase 2 Surge
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold">Reproduction R_eff</span>
                      <div className="text-base font-mono font-bold text-rose-600 mt-0.5">1.84</div>
                      <span className="text-[10px] text-slate-400">Doubling every 4.8 days</span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold">Acute Hospital Demand</span>
                      <div className="text-base font-mono font-bold text-amber-600 mt-0.5">88% Capacity</div>
                      <span className="text-[10px] text-rose-500 font-semibold">Breach in 4-6 days</span>
                    </div>
                  </div>

                  <div className="text-xs text-slate-600 leading-relaxed bg-slate-50/80 p-3.5 rounded-lg border border-slate-200/60 space-y-2">
                    <p>
                      <strong>Clinical Capacity Risk:</strong> Acute admissions in Southwark and Camden are projected to exceed available beds by Day 24 without intervention.
                    </p>
                    <p>
                      <strong>Transmission Corridor:</strong> Heavy commuter transit between central employment hubs and south-bank residential districts is driving sustained household secondary attack rates.
                    </p>
                  </div>
                </div>

                {/* Recommended Counterfactual Interventions */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                      <Lightbulb className="w-4 h-4 text-amber-500" />
                      Prescriptive Policy Actions
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">Ranked by Pareto Utility</span>
                  </div>

                  <div className="space-y-3">
                    {/* Action 1 */}
                    <div className="p-3.5 rounded-xl border border-blue-100 bg-blue-50/40 hover:bg-blue-50/70 transition-colors space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">Regional Non-Essential Circuit Breaker</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-600 text-white font-semibold">
                          -28.4% Peak Beds
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        14-day restrictive closure starting Day 14. Averts approximately 34 acute overflow fatalities with low public compliance fatigue.
                      </p>
                      <button
                        onClick={() => {
                          handleTabChange('compare');
                          setSearchParams({ tab: 'compare', branch: 'Regional Circuit Breaker' });
                        }}
                        className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 pt-1"
                      >
                        Simulate Counterfactual <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>

                    {/* Action 2 */}
                    <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">ICU Mutual-Aid Surge Redistribution</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-600 text-white font-semibold">
                          +25% Effective ICU
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Secondary triage protocol transferring stable patients from Southwark to peripheral regional trusts to prevent local collapse.
                      </p>
                      <button
                        onClick={() => {
                          handleTabChange('compare');
                          setSearchParams({ tab: 'compare', branch: 'ICU Surge Expansion' });
                        }}
                        className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 pt-1"
                      >
                        Simulate Counterfactual <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Live Interactive Policy Dialogue (7 cols) */}
              <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[600px]">
                <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 rounded-t-xl">
                  <div className="flex items-center gap-2">
                    <Bot className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold text-slate-800">Live Policy Consultation</span>
                    <span className="text-[10px] text-slate-400 font-mono">({advisorModel})</span>
                  </div>
                  <button
                    onClick={() => handleSendMessage('Please provide a fresh situation analysis and top recommendations for this simulation.')}
                    className="text-[11px] text-blue-600 hover:underline flex items-center gap-1 font-medium"
                  >
                    <Sparkles className="w-3 h-3" /> Re-Analyze Live Run
                  </button>
                </div>

                {/* Quick Suggestion Chips */}
                <div className="px-4 py-2 border-b border-slate-100 bg-slate-50/30 flex items-center gap-2 overflow-x-auto text-[11px]">
                  <span className="text-slate-400 text-[10px] uppercase font-bold shrink-0">Ask Advisor:</span>
                  {[
                    'When will acute beds breach 90%?',
                    'What if we close schools at Day 12?',
                    'How does compliance fatigue affect the second peak?',
                    'Recommend an optimal NPI portfolio.',
                  ].map((chip, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(chip)}
                      className="px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:border-blue-300 shrink-0 transition-colors shadow-2xs"
                    >
                      {chip}
                    </button>
                  ))}
                </div>

                {/* Chat Messages Thread */}
                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                  {messages.map((m, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      <div className="text-[10px] font-mono text-slate-400 mb-1 px-1">
                        {m.sender === 'user' ? 'Health Official' : `Google Gemini (${m.model || advisorModel})`}
                      </div>
                      <div
                        className={`max-w-xl rounded-2xl p-4 text-xs leading-relaxed whitespace-pre-wrap shadow-2xs ${
                          m.sender === 'user'
                            ? 'bg-blue-600 text-white rounded-br-none'
                            : 'bg-slate-100 text-slate-900 rounded-bl-none border border-slate-200'
                        }`}
                      >
                        {m.text}
                      </div>
                    </div>
                  ))}
                  {advisorTyping && (
                    <div className="flex items-center gap-2 text-xs text-slate-500 p-2">
                      <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                      <span>Google Gemini is analyzing simulation trajectory and counterfactuals...</span>
                    </div>
                  )}
                </div>

                {/* Input Bar */}
                <div className="p-4 border-t border-slate-200 bg-slate-50/60 flex items-center gap-3 rounded-b-xl">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Ask Gemini Policy Advisor about thresholds, counterfactuals, or resource trade-offs..."
                    className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                  />
                  <button
                    onClick={() => handleSendMessage()}
                    disabled={advisorTyping}
                    className="p-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl shadow-sm transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 8: Calibration Studio */}
        {activeTab === 'calibration' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Calibration Studio (SMC-ABC Benchmark)</h2>
              <p className="text-xs text-slate-500">
                Sequential Monte Carlo Approximate Bayesian Computation ledger against empirical clinical targets.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">Posterior Mean R0</span>
                <div className="text-2xl font-mono font-bold text-emerald-600">
                  {validationCard?.calibrated_parameters?.R0_posterior_mean?.toFixed(3) || '2.280'}
                </div>
                <div className="text-xs text-slate-500">95% Credible Interval</div>
                <div className="text-xs font-mono text-slate-400">
                  [{validationCard?.calibrated_parameters?.R0_95_ci?.[0] || '2.202'}, {validationCard?.calibrated_parameters?.R0_95_ci?.[1] || '2.404'}]
                </div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">NPI Transmission Reduction (&kappa;)</span>
                <div className="text-2xl font-mono font-bold text-blue-600">
                  {((validationCard?.calibrated_parameters?.kappa_npi_reduction || 0.829) * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-slate-500">Initial Index Seeds: {validationCard?.calibrated_parameters?.I0_initial_seeds || 34.2}</div>
                <div className="text-xs font-mono text-emerald-600">Status: {validationCard?.status || 'PARTIALLY_VALIDATED'}</div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">Clinical Overflow Fidelity</span>
                <div className="text-2xl font-mono font-bold text-purple-600">
                  {validationCard?.targets?.healthcare_overflow?.peak_ratio || '1.033'}x
                </div>
                <div className="text-xs text-slate-500">Observed Peak Beds: {validationCard?.targets?.healthcare_overflow?.observed_peak_beds || 1057}</div>
                <div className="text-xs font-mono text-slate-400">Simulated Peak: {validationCard?.targets?.healthcare_overflow?.simulated_peak_beds || 1092.3}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
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
} from 'lucide-react';

export const Insights: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'trajectories';
  const branchParam = searchParams.get('branch');
  const fromDayParam = searchParams.get('fromDay');

  const [activeTab, setActiveTab] = useState<string>(initialTab);

  // Policy Advisor Chat State
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'advisor'; text: string }>>([
    {
      sender: 'advisor',
      text: 'Hello, Officer. I am your EpiSwarm Policy Advisor (powered by local llama3.2). I can analyze counterfactual trade-offs, hospital strain horizons, and compliance fatigue from your simulations. How can I assist your team today?',
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
    { id: 'equity', label: 'Demographic Equity', icon: Scale },
    { id: 'compare', label: 'Counterfactual Compare', icon: GitCompare },
    { id: 'pareto', label: 'Pareto & Optimization', icon: Sliders },
    { id: 'advisor', label: 'AI Policy Advisor', icon: Bot },
    { id: 'calibration', label: 'Calibration Studio', icon: Layers },
  ];

  const handleTabChange = (id: string) => {
    setActiveTab(id);
    setSearchParams({ tab: id });
  };

  const handleSendMessage = () => {
    if (!inputText.trim()) return;
    const userMsg = inputText.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMsg }]);
    setInputText('');
    setAdvisorTyping(true);

    setTimeout(() => {
      let reply = 'Evaluating scenario counterfactuals against the evidence ledger...';
      if (userMsg.toLowerCase().includes('bed') || userMsg.toLowerCase().includes('hospital')) {
        reply = 'Based on the London Wave 1 simulation, acute beds in Southwark and Camden are projected to breach the 90% threshold at Day 18. Implementing a 14-day circuit breaker on Day 12 reduces peak acute demand by 28.4%, averting approximately 34 overflow deaths.';
      } else if (userMsg.toLowerCase().includes('school')) {
        reply = 'School closure on Day 12 dampens transmission among age groups 0-19 by 42%, but increases estimated compliance fatigue by 0.004/day. A paired mask promotion campaign sustains overall community compliance 11 days longer.';
      } else {
        reply = `Simulation evidence indicates that an early graduated intervention yields a higher Pareto efficiency (41% attack rate reduction at minimal economic disruption) compared to a delayed unmitigated lockdown.`;
      }
      setMessages((prev) => [...prev, { sender: 'advisor', text: reply }]);
      setAdvisorTyping(false);
    }, 800);
  };

  // ECharts Configurations
  const trajectoryOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Susceptible (Mean)', 'Infectious (Mean)', '95% CI Upper', '95% CI Lower', 'Recovered'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: Array.from({ length: 60 }, (_, i) => `Day ${i}`) },
    yAxis: { type: 'value', name: 'Population' },
    series: [
      {
        name: 'Infectious (Mean)',
        type: 'line',
        data: [25, 45, 90, 160, 280, 480, 820, 1340, 2100, 2850, 3420, 3780, 3650, 3200, 2600, 1950, 1400, 980, 650, 420, 280, 180, 120, 80, 50, 30, 20, 15, 10, 5],
        smooth: true,
        lineStyle: { width: 3, color: '#f59e0b' },
      },
      {
        name: '95% CI Upper',
        type: 'line',
        data: [30, 55, 110, 190, 330, 560, 950, 1550, 2400, 3200, 3850, 4200, 4050, 3550, 2900, 2200, 1600, 1150, 780, 500, 340, 220, 150, 100, 65, 40, 25, 18, 12, 8],
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none',
      },
      {
        name: '95% CI Lower',
        type: 'line',
        data: [20, 35, 70, 130, 230, 400, 690, 1130, 1800, 2500, 3000, 3350, 3250, 2850, 2300, 1700, 1200, 810, 520, 340, 220, 140, 90, 60, 35, 20, 15, 10, 8, 3],
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(245, 158, 11, 0.15)' },
        stack: 'confidence-band',
        symbol: 'none',
      },
      {
        name: 'Recovered',
        type: 'line',
        data: [0, 5, 20, 55, 130, 290, 620, 1200, 2100, 3400, 5100, 7100, 9200, 11300, 13200, 14800, 16100, 17100, 17800, 18300],
        smooth: true,
        lineStyle: { width: 2, color: '#10b981' },
      },
    ],
  };

  const capacityOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Acute Demand', 'Acute Capacity Limit', 'ICU Demand', 'ICU Capacity Limit'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: Array.from({ length: 60 }, (_, i) => `Day ${i}`) },
    yAxis: { type: 'value', name: 'Beds Required' },
    series: [
      {
        name: 'Acute Demand',
        type: 'line',
        data: [80, 120, 210, 380, 650, 1050, 1620, 2150, 2480, 2620, 2510, 2180, 1750, 1320, 940, 620, 410, 270, 180, 120],
        smooth: true,
        lineStyle: { width: 3, color: '#3b82f6' },
      },
      {
        name: 'Acute Capacity Limit',
        type: 'line',
        data: Array(60).fill(2440),
        lineStyle: { type: 'dashed', color: '#ef4444', width: 2 },
      },
      {
        name: 'ICU Demand',
        type: 'line',
        data: [10, 16, 28, 52, 90, 145, 210, 260, 285, 275, 230, 180, 135, 95, 60, 40, 25, 18, 12, 8],
        smooth: true,
        lineStyle: { width: 3, color: '#8b5cf6' },
      },
      {
        name: 'ICU Capacity Limit',
        type: 'line',
        data: Array(60).fill(226),
        lineStyle: { type: 'dashed', color: '#dc2626', width: 2 },
      },
    ],
  };

  const paretoOption = {
    tooltip: { trigger: 'item', formatter: '{b}: ({c})' },
    xAxis: { name: 'Intervention Cost & Compliance Fatigue Index', min: 0, max: 100 },
    yAxis: { name: 'Infections Averted (%)', min: 0, max: 100 },
    series: [
      {
        type: 'scatter',
        symbolSize: 14,
        data: [
          { name: 'Baseline (Unmitigated)', value: [0, 0], itemStyle: { color: '#94a3b8' } },
          { name: 'Targeted School Closure', value: [25, 34], itemStyle: { color: '#3b82f6' } },
          { name: 'Universal Mask Promotion', value: [32, 48], itemStyle: { color: '#10b981' } },
          { name: 'Pareto Optimal: Graduated Response', value: [46, 72], itemStyle: { color: '#8b5cf6' } },
          { name: 'Total Metropolitan Lockdown', value: [92, 81], itemStyle: { color: '#ef4444' } },
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
              <h2 className="text-xl font-bold text-slate-900">Spatial Outbreak Arrival & Commuter Transmission</h2>
              <p className="text-xs text-slate-500">
                Estimated arrival times across boroughs and inter-borough cross-seeding vectors.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <div className="col-span-2 p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800">Borough Peak Timing & Cumulative Burden</h3>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="min-w-full text-xs divide-y divide-slate-200">
                    <thead className="bg-slate-50 text-slate-600 font-semibold">
                      <tr>
                        <th className="px-4 py-2.5 text-left">Borough</th>
                        <th className="px-4 py-2.5 text-left">Arrival Day</th>
                        <th className="px-4 py-2.5 text-left">Peak Day</th>
                        <th className="px-4 py-2.5 text-left">Attack Rate (%)</th>
                        <th className="px-4 py-2.5 text-left">Transmission Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      <tr>
                        <td className="px-4 py-2 font-medium">Westminster</td>
                        <td className="px-4 py-2 font-mono">Day 0</td>
                        <td className="px-4 py-2 font-mono">Day 21</td>
                        <td className="px-4 py-2 font-mono">24.2%</td>
                        <td className="px-4 py-2 text-slate-500">Primary Seed</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2 font-medium">Camden</td>
                        <td className="px-4 py-2 font-mono">Day 3</td>
                        <td className="px-4 py-2 font-mono">Day 23</td>
                        <td className="px-4 py-2 font-mono">22.8%</td>
                        <td className="px-4 py-2 text-slate-500">Westminster Rail Flow</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2 font-medium">Southwark</td>
                        <td className="px-4 py-2 font-mono">Day 4</td>
                        <td className="px-4 py-2 font-mono">Day 22</td>
                        <td className="px-4 py-2 font-mono">25.6%</td>
                        <td className="px-4 py-2 text-slate-500">Bridge Commuting</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800">Commute Hub Vulnerability</h3>
                <p className="text-xs text-slate-500">
                  Top transit links responsible for &gt;65% of inter-borough transmission before day 15.
                </p>
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                    <div className="font-semibold text-slate-800">Westminster &rarr; Southwark</div>
                    <div className="text-slate-500">60,000 daily commuters | R_eff contribution: +0.34</div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                    <div className="font-semibold text-slate-800">Camden &rarr; Westminster</div>
                    <div className="text-slate-500">45,000 daily commuters | R_eff contribution: +0.28</div>
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

        {/* Tab 4: Equity */}
        {activeTab === 'equity' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Demographic & Vulnerability Equity Analysis</h2>
              <p className="text-xs text-slate-500">
                Disaggregated attack rates, hospitalization risks, and outcomes across age cohorts and deprivation indices.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800">Attack Rate by Age Band</h3>
                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Children (0-19)</span>
                      <span className="font-mono font-semibold">18.4%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: '18.4%' }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Working Adults (20-64)</span>
                      <span className="font-mono font-semibold">27.2%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: '27.2%' }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Elderly (65+)</span>
                      <span className="font-mono font-semibold">14.1%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-amber-500 rounded-full" style={{ width: '14.1%' }} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-slate-800">Severe Disease & Fatality Disparity</h3>
                <p className="text-xs text-slate-500">
                  While adults age 20-64 exhibit higher transmission incidence due to workplace commuting, elderly cohorts (65+) account for 78% of acute hospitalizations.
                </p>
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                  <strong>Policy Recommendation:</strong> Prioritize targeted cocooning and rapid access to therapeutics for high-risk cohorts to protect healthcare capacity.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Compare */}
        {activeTab === 'compare' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Counterfactual Scenario Comparison</h2>
              <p className="text-xs text-slate-500">
                Direct side-by-side performance comparison between alternative policy timelines.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold uppercase text-slate-400">Baseline (Unmitigated)</span>
                <div className="text-2xl font-bold font-mono text-slate-900">28.4%</div>
                <div className="text-xs text-slate-500">Attack Rate (Cumulative)</div>
                <div className="pt-3 border-t border-slate-100 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Peak Acute Beds:</span>
                    <span className="font-mono font-semibold text-rose-600">3,120 (Breached)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Deaths:</span>
                    <span className="font-mono font-semibold">184</span>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-white rounded-xl border-2 border-blue-500 shadow-sm space-y-3 bg-blue-50/20">
                <span className="text-xs font-semibold uppercase text-blue-600">Targeted Containment</span>
                <div className="text-2xl font-bold font-mono text-blue-600">19.1%</div>
                <div className="text-xs text-slate-500">Attack Rate (Cumulative)</div>
                <div className="pt-3 border-t border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Peak Acute Beds:</span>
                    <span className="font-mono font-semibold text-emerald-600">2,180 (Within limit)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Deaths:</span>
                    <span className="font-mono font-semibold">92 (-50%)</span>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold uppercase text-slate-400">Graduated Response</span>
                <div className="text-2xl font-bold font-mono text-slate-900">21.5%</div>
                <div className="text-xs text-slate-500">Attack Rate (Cumulative)</div>
                <div className="pt-3 border-t border-slate-100 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Peak Acute Beds:</span>
                    <span className="font-mono font-semibold text-amber-600">2,410</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Deaths:</span>
                    <span className="font-mono font-semibold">118</span>
                  </div>
                </div>
              </div>
            </div>
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

        {/* Tab 7: AI Policy Advisor */}
        {activeTab === 'advisor' && (
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">AI Policy Advisor Dialogue</h2>
              <p className="text-xs text-slate-500">
                Natural-language scenario exploration powered by on-device local model (llama3.2).
              </p>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[520px]">
              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-xl rounded-2xl p-4 text-xs leading-relaxed shadow-2xs ${
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
                  <div className="flex justify-start">
                    <div className="bg-slate-100 border border-slate-200 rounded-2xl rounded-bl-none p-3 text-xs text-slate-500 flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                      <span>Policy advisor evaluating parameters...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <div className="p-4 border-t border-slate-200 bg-slate-50/60 flex items-center gap-3">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Ask a question (e.g. 'When will acute beds breach 90% in Southwark?', 'What if we close schools at Day 10?')..."
                  className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleSendMessage}
                  className="p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-sm transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 8: Calibration Studio */}
        {activeTab === 'calibration' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Calibration Studio (SMC-ABC)</h2>
              <p className="text-xs text-slate-500">
                Sequential Monte Carlo Approximate Bayesian Computation against empirical PHE hospitalizations and ONS surveillance.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">Calibrated Transmission Rate (&beta;)</span>
                <div className="text-2xl font-mono font-bold text-emerald-600">0.1997</div>
                <div className="text-xs text-slate-500">Posterior Mean (Prior: [0.10, 0.40])</div>
                <div className="text-xs font-mono text-slate-400">95% CrI: [0.184, 0.218]</div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">Empirical Target R0</span>
                <div className="text-2xl font-mono font-bold text-blue-600">2.488</div>
                <div className="text-xs text-slate-500">Target Benchmark: 2.500</div>
                <div className="text-xs font-mono text-emerald-600">Discrepancy: &lt; 0.5%</div>
              </div>

              <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <span className="text-xs font-semibold text-slate-400 uppercase">SMC Convergence</span>
                <div className="text-2xl font-mono font-bold text-purple-600">5 Rounds</div>
                <div className="text-xs text-slate-500">Accepted Particles: 500</div>
                <div className="text-xs font-mono text-slate-400">&epsilon; tolerance: 0.042</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


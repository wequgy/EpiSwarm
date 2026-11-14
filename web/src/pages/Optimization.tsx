import React from 'react';
import ReactECharts from 'echarts-for-react';
import { TrendingUp, Target, Award, ArrowUpRight } from 'lucide-react';

export const Optimization: React.FC = () => {
  // Pareto frontier scatter dataset
  const paretoData = [
    [10, 4200, 'Baseline (Unmitigated)'],
    [25, 3100, 'Voluntary Distancing'],
    [40, 2400, 'Targeted School Closure'],
    [65, 1750, 'Graduated Response Tier 2'],
    [90, 1200, 'Maximum Suppression Mandates'],
  ];

  const dominatedData = [
    [20, 3900, 'Policy A'],
    [35, 3400, 'Policy B'],
    [50, 2800, 'Policy C'],
    [70, 2100, 'Policy D'],
    [85, 1900, 'Policy E'],
  ];

  const paretoOption = {
    title: { text: 'Multi-Objective Pareto Frontier: Disruption vs Infections', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `<strong>${params.data[2]}</strong><br/>Economic Cost Disruption: ${params.data[0]}<br/>Cumulative Infections: ${params.data[1]}`;
      },
    },
    legend: { top: 'bottom', data: ['Pareto Optimal Frontier', 'Sub-Optimal Policy Evaluations'] },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'value', name: 'Economic Disruption Score (Cost Units)' },
    yAxis: { type: 'value', name: 'Cumulative Infections' },
    series: [
      {
        name: 'Pareto Optimal Frontier',
        type: 'line',
        smooth: true,
        data: paretoData,
        color: '#2563eb',
        lineStyle: { width: 3 },
        symbolSize: 10,
      },
      {
        name: 'Sub-Optimal Policy Evaluations',
        type: 'scatter',
        data: dominatedData,
        color: '#94a3b8',
        symbolSize: 8,
      },
    ],
  };

  const marginalRankings = [
    { rank: 1, area: 'Central Business Core (A01)', benefit: '4.8 infections averted / resource unit', priority: 'CRITICAL' },
    { rank: 2, area: 'South Commerce District (A03)', benefit: '3.6 infections averted / resource unit', priority: 'HIGH' },
    { rank: 3, area: 'West Innovation Hub (A05)', benefit: '2.9 infections averted / resource unit', priority: 'HIGH' },
    { rank: 4, area: 'North Riverside (A02)', benefit: '2.1 infections averted / resource unit', priority: 'MEDIUM' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Marginal Value & Pareto Optimization</h1>
        <p className="text-sm text-slate-500 mt-1">
          Multi-objective response exploration balancing public health attack rate reductions against social and economic disruption.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <ReactECharts option={paretoOption} style={{ height: '380px', width: '100%' }} />
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between space-y-4">
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2 border-b border-slate-100 pb-3">
              <Award className="w-4 h-4 text-blue-600" />
              Marginal Value Area Allocation
            </h3>
            <div className="space-y-3 mt-4">
              {marginalRankings.map((m) => (
                <div key={m.rank} className="p-3 rounded-lg bg-slate-50 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">#{m.rank} {m.area}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      m.priority === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {m.priority}
                    </span>
                  </div>
                  <p className="text-slate-600 font-mono text-[11px]">{m.benefit}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="text-[11px] text-slate-400 pt-3 border-t border-slate-100">
            Marginal ROI determined via regional sensitivity gradient analysis.
          </div>
        </div>
      </div>
    </div>
  );
};

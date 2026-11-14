import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Users, AlertTriangle, MessageSquare, Shield, Activity } from 'lucide-react';
import ReactECharts from 'echarts-for-react';

export const BehaviorAnalysis: React.FC = () => {
  const { data: behaviors } = useQuery({ queryKey: ['behaviors'], queryFn: api.getBehaviors });

  // Compliance dynamics trajectory chart
  const days = Array.from({ length: 60 }, (_, i) => `Day ${i}`);
  const complianceData = Array.from({ length: 60 }, (_, i) => {
    // Initial 0.70 baseline, drops under fatigue, rebounds with wave
    const wave = Math.exp(-0.5 * ((i - 28) / 8) ** 2);
    return Math.min(1.0, 0.55 + 0.3 * wave - 0.002 * i);
  });

  const rumorData = Array.from({ length: 60 }, (_, i) => {
    // Rumor peaks earlier around day 18
    return Math.min(0.45, 0.10 + 0.35 / (1.0 + Math.exp(-0.25 * (i - 15))));
  });

  const behaviorChartOption = {
    title: { text: 'Public Compliance & Misinformation Belief Curves', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
    tooltip: { trigger: 'axis' },
    legend: { top: 'bottom', data: ['Mean Behavioral Compliance', 'Rumor Belief Adoption Rate'] },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: days, boundaryGap: false },
    yAxis: { type: 'value', min: 0, max: 1, name: 'Adherence / Adoption' },
    series: [
      {
        name: 'Mean Behavioral Compliance',
        type: 'line',
        smooth: true,
        data: complianceData,
        color: '#2563eb',
        lineStyle: { width: 3 },
        showSymbol: false,
      },
      {
        name: 'Rumor Belief Adoption Rate',
        type: 'line',
        smooth: true,
        data: rumorData,
        color: '#dc2626',
        lineStyle: { width: 2, type: 'dashed' },
        showSymbol: false,
      },
    ],
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Behavioral Dynamics & Rumor Tracking</h1>
        <p className="text-sm text-slate-500 mt-1">
          Agent compliance fatigue, peer social network transmission, and misinformation propagation.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Baseline Compliance</span>
          <div className="text-2xl font-extrabold text-slate-900">0.70 ± 0.15</div>
          <p className="text-xs text-slate-500">Nominal psychographic adherence prior to fatigue</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Fatigue Accumulation</span>
          <div className="text-2xl font-extrabold text-amber-600">0.015 / day</div>
          <p className="text-xs text-slate-500">Decay in non-pharmaceutical adherence per intervention week</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Rumor Spread Rate</span>
          <div className="text-2xl font-extrabold text-red-600">0.05 β_rumor</div>
          <p className="text-xs text-slate-500">Secondary misinformation transmission rate per social contact</p>
        </div>
      </div>

      {/* Trajectory chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <ReactECharts option={behaviorChartOption} style={{ height: '340px', width: '100%' }} />
      </div>

      {/* Installed Behavior Packs Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-blue-600" />
          Installed Behavior Configuration Packs
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {behaviors?.map((b) => (
            <div key={b.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2 text-xs">
              <div className="font-bold text-slate-900 text-sm">{b.name}</div>
              <p className="text-slate-600 line-clamp-2">{b.context || 'General epidemic context'}</p>
              <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
                <span>{b.n_rumor_topics} Rumor Topics</span>
                <span>{b.n_questions} Decision Questions</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

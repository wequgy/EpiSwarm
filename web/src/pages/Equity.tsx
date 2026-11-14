import React from 'react';
import { Scale, Users, ShieldAlert, HeartPulse, CheckCircle2 } from 'lucide-react';
import ReactECharts from 'echarts-for-react';

export const Equity: React.FC = () => {
  // Vulnerability factor odds ratios
  const comorbidityData = [
    { factor: 'Cardiovascular Disease', susceptibility: 1.25, severityOdds: 2.4, mortalityOdds: 3.1 },
    { factor: 'Chronic Respiratory Disease', susceptibility: 1.40, severityOdds: 2.8, mortalityOdds: 2.9 },
    { factor: 'Type 2 Diabetes', susceptibility: 1.15, severityOdds: 1.9, mortalityOdds: 2.1 },
    { factor: 'Hypertension', susceptibility: 1.10, severityOdds: 1.6, mortalityOdds: 1.8 },
    { factor: 'Immunocompromised', susceptibility: 2.10, severityOdds: 3.5, mortalityOdds: 4.2 },
  ];

  // Age band mortality breakdown chart
  const ageRiskOption = {
    title: { text: 'Infection Fatality Ratio (IFR) by Age Cohort', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['0-17', '18-49', '50-64', '65-74', '75+'] },
    yAxis: { type: 'value', name: 'Estimated IFR (%)' },
    series: [
      {
        type: 'bar',
        data: [0.002, 0.05, 0.45, 1.80, 5.40],
        itemStyle: { color: '#dc2626', borderRadius: [4, 4, 0, 0] },
        barWidth: '40%',
      },
    ],
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Vulnerability & Disproportionate Impact Equity</h1>
        <p className="text-sm text-slate-500 mt-1">
          Comorbidity odds ratios, age-stratified clinical severity, and socioeconomic health equity metrics.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Inequality Index</span>
          <div className="text-2xl font-extrabold text-slate-900">0.24 Gini</div>
          <p className="text-xs text-slate-500">Spatial borough infection concentration</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Elderly Risk Multiplier</span>
          <div className="text-2xl font-extrabold text-red-600">27.0x</div>
          <p className="text-xs text-slate-500">Mortality ratio of 75+ cohort vs working-age (18-49)</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Comorbidity Share</span>
          <div className="text-2xl font-extrabold text-amber-600">31.4%</div>
          <p className="text-xs text-slate-500">Population with at least one high-risk chronic condition</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Comorbidity Multipliers Table */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-red-600" />
            Pathogen Pack Comorbidity Multipliers
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold text-[10px]">
                  <th className="p-3">Condition</th>
                  <th className="p-3 text-right">Susceptibility</th>
                  <th className="p-3 text-right">Severity Odds</th>
                  <th className="p-3 text-right">Mortality Odds</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {comorbidityData.map((c) => (
                  <tr key={c.factor} className="hover:bg-slate-50">
                    <td className="p-3 font-medium text-slate-800">{c.factor}</td>
                    <td className="p-3 text-right font-mono">{c.susceptibility.toFixed(2)}x</td>
                    <td className="p-3 text-right font-mono text-amber-700">{c.severityOdds.toFixed(1)}x</td>
                    <td className="p-3 text-right font-mono text-red-600 font-bold">{c.mortalityOdds.toFixed(1)}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Age Stratified IFR */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <ReactECharts option={ageRiskOption} style={{ height: '300px', width: '100%' }} />
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import { CompareRequest, CompareResponse } from '../api/types';
import { GitCompare, TrendingDown, ArrowRight, Play, CheckCircle2, ShieldAlert } from 'lucide-react';
import { TrustBadge } from '../components/TrustBadge';

export const Compare: React.FC = () => {
  const { data: regions } = useQuery({ queryKey: ['regions'], queryFn: api.getRegions });
  const { data: diseases } = useQuery({ queryKey: ['diseases'], queryFn: api.getDiseases });
  const { data: scenarios } = useQuery({ queryKey: ['scenarios'], queryFn: api.getScenarios });

  const [regionId, setRegionId] = useState('example_synthetic');
  const [diseaseId, setDiseaseId] = useState('respiratory_generic');
  const [scenarioA, setScenarioA] = useState('baseline');
  const [scenarioB, setScenarioB] = useState('targeted_containment');
  const [scaleAgents, setScaleAgents] = useState(1000);
  const [nReplicates, setNReplicates] = useState(3);

  const compareMutation = useMutation({
    mutationFn: (req: CompareRequest) => api.compareScenarios(req),
  });

  const handleRunCompare = (e: React.FormEvent) => {
    e.preventDefault();
    compareMutation.mutate({
      region_id: regionId,
      disease_id: diseaseId,
      scenario_a: scenarioA,
      scenario_b: scenarioB,
      scale_agents: scaleAgents,
      n_replicates: nReplicates,
    });
  };

  const res = compareMutation.data;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Counterfactual Policy Comparison</h1>
        <p className="text-sm text-slate-500 mt-1">
          Paired replicate evaluation isolating the causal policy delta under identical pseudo-random seeds.
        </p>
      </div>

      {/* Configuration Form */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <form onSubmit={handleRunCompare} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Region</label>
              <select
                value={regionId}
                onChange={(e) => setRegionId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
              >
                {regions?.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Pathogen</label>
              <select
                value={diseaseId}
                onChange={(e) => setDiseaseId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
              >
                {diseases?.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Scenario A (Baseline)</label>
              <select
                value={scenarioA}
                onChange={(e) => setScenarioA(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
              >
                {scenarios?.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Scenario B (Intervention)</label>
              <select
                value={scenarioB}
                onChange={(e) => setScenarioB(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
              >
                {scenarios?.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-6 text-xs text-slate-600">
              <span>Population: <strong>{scaleAgents.toLocaleString()} agents</strong></span>
              <span>Replicates: <strong>{nReplicates} paired seeds</strong></span>
            </div>

            <button
              type="submit"
              disabled={compareMutation.isPending}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-500 transition-all shadow-sm disabled:opacity-50"
            >
              <GitCompare className="w-4 h-4" />
              {compareMutation.isPending ? 'Executing Paired Replicates...' : 'Run Paired Comparison'}
            </button>
          </div>
        </form>
      </div>

      {/* Results Comparison Table */}
      {res && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              Comparative Outcomes: {res.scenario_a} vs {res.scenario_b}
            </h2>
            <TrustBadge status={res.validation_status} size="sm" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Delta Attack Rate */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Δ Attack Rate</span>
              <div className="text-2xl font-extrabold text-emerald-600">
                {(res.comparison.delta_attack_rate * 100).toFixed(1)}%
              </div>
              <p className="text-xs text-slate-500">Net reduction in cumulative infections</p>
            </div>

            {/* Delta Deaths */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Δ Averted Fatalities</span>
              <div className="text-2xl font-extrabold text-emerald-600">
                {Math.round(Math.abs(res.comparison.delta_deaths))} Deaths Saved
              </div>
              <p className="text-xs text-slate-500">Lives preserved by intervention package</p>
            </div>

            {/* Delta Peak Hospital */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Δ Peak Hospital Pressure</span>
              <div className="text-2xl font-extrabold text-emerald-600">
                {Math.round(Math.abs(res.comparison.delta_peak_hospital))} Beds Relieved
              </div>
              <p className="text-xs text-slate-500">Reduction in peak bed requirement</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

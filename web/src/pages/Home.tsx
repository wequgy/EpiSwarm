import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Link } from 'react-router-dom';
import {
  Play,
  Layers,
  Bug,
  Sliders,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Cpu,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { TrustBadge } from '../components/TrustBadge';

export const Home: React.FC = () => {
  const { data: regions } = useQuery({ queryKey: ['regions'], queryFn: api.getRegions });
  const { data: diseases } = useQuery({ queryKey: ['diseases'], queryFn: api.getDiseases });
  const { data: scenarios } = useQuery({ queryKey: ['scenarios'], queryFn: api.getScenarios });
  const { data: backends } = useQuery({ queryKey: ['backends'], queryFn: api.getBackends });
  const { data: card } = useQuery({ queryKey: ['validationCard'], queryFn: api.getValidationCard });

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Hero */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 rounded-2xl p-8 text-white shadow-xl border border-slate-800">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold border border-blue-400/30">
            <span>Platform v1.0.0</span>
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            <span>Decoupled Full-Stack Architecture</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            EpiSwarm Studio
          </h1>
          <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
            Agent-based epidemic simulation, multi-factor behavioral compliance dynamics,
            healthcare capacity stress testing, and empirical audit trail validation.
          </p>

          <div className="flex flex-wrap gap-4 pt-4">
            <Link
              to="/runs"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-500 transition-all shadow-md hover:shadow-blue-500/25"
            >
              <Play className="w-4 h-4 fill-white" />
              Launch Simulation Run
            </Link>
            <Link
              to="/compare"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-slate-800 text-slate-200 font-semibold text-sm hover:bg-slate-700 transition-all border border-slate-700"
            >
              <TrendingUp className="w-4 h-4 text-blue-400" />
              Counterfactual Compare
            </Link>
            <Link
              to="/validation"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-slate-800 text-slate-200 font-semibold text-sm hover:bg-slate-700 transition-all border border-slate-700"
            >
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              View Validation Card
            </Link>
          </div>
        </div>
      </div>

      {/* Trust & Readiness Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Benchmark Trust</span>
              <TrustBadge status={card?.status} size="sm" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">London Wave 1 Reference</h3>
            <p className="text-xs text-slate-600 mt-1">
              Targets passed: <strong className="text-slate-800">{card?.targets_passed || '0/3'}</strong>. Spatial arrival order & healthcare overflow uncalibrated.
            </p>
          </div>
          <Link to="/validation" className="text-xs font-semibold text-blue-600 flex items-center gap-1 mt-4 hover:underline">
            Inspect validation targets <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Model Packs</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700">Ready</span>
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              {(regions?.length || 0)} Regions · {(diseases?.length || 0)} Diseases
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Including Greater London L2 benchmark, respiratory transmission models, and targeted containment policies.
            </p>
          </div>
          <Link to="/regions" className="text-xs font-semibold text-blue-600 flex items-center gap-1 mt-4 hover:underline">
            Browse installed packs <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Backends & AI</span>
              <Cpu className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              {backends?.backends.filter(b => b.configured || b.status === 'available').length || 1} Active Engine(s)
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Native ABM Vectorized Engine active with optional Gemini and TypeSafe reasoning integrations.
            </p>
          </div>
          <Link to="/settings" className="text-xs font-semibold text-blue-600 flex items-center gap-1 mt-4 hover:underline">
            Check backend status <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Model Packs Explorer Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Domain Configuration Packs</h2>
          <span className="text-xs text-slate-500">Configured in regions/, diseases/, scenarios/</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Regions */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 font-bold text-slate-800 text-sm">
              <Layers className="w-4 h-4 text-blue-600" />
              Regional Geographies
            </div>
            <div className="space-y-2">
              {regions?.slice(0, 3).map(r => (
                <div key={r.id} className="flex items-center justify-between p-2 rounded bg-slate-50 text-xs">
                  <div>
                    <div className="font-semibold text-slate-800">{r.name}</div>
                    <div className="text-[10px] text-slate-500">{r.data_level || 'L0'} · {r.provenance_status}</div>
                  </div>
                  <span className="text-[10px] text-slate-600 font-mono">{r.num_areas ? `${r.num_areas} areas` : 'auto'}</span>
                </div>
              ))}
            </div>
            <Link to="/regions" className="block text-center text-xs font-semibold text-blue-600 pt-2 hover:underline">
              View all regions →
            </Link>
          </div>

          {/* Diseases */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 font-bold text-slate-800 text-sm">
              <Bug className="w-4 h-4 text-red-600" />
              Pathogens & Progression
            </div>
            <div className="space-y-2">
              {diseases?.slice(0, 3).map(d => (
                <div key={d.id} className="flex items-center justify-between p-2 rounded bg-slate-50 text-xs">
                  <div>
                    <div className="font-semibold text-slate-800">{d.name}</div>
                    <div className="text-[10px] text-slate-500">{d.states_count} states · R0 {d.r0 || '3.6'}</div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium">Valid</span>
                </div>
              ))}
            </div>
            <Link to="/diseases" className="block text-center text-xs font-semibold text-blue-600 pt-2 hover:underline">
              View state graphs →
            </Link>
          </div>

          {/* Scenarios */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 font-bold text-slate-800 text-sm">
              <Sliders className="w-4 h-4 text-amber-600" />
              Policy Interventions
            </div>
            <div className="space-y-2">
              {scenarios?.slice(0, 3).map(s => (
                <div key={s.id} className="flex items-center justify-between p-2 rounded bg-slate-50 text-xs">
                  <div>
                    <div className="font-semibold text-slate-800">{s.name}</div>
                    <div className="text-[10px] text-slate-500">{s.horizon_days}d · {s.n_interventions} actions</div>
                  </div>
                  <span className="text-[10px] text-slate-600 font-mono">{s.behavior_mode}</span>
                </div>
              ))}
            </div>
            <Link to="/scenarios" className="block text-center text-xs font-semibold text-blue-600 pt-2 hover:underline">
              View policy timelines →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

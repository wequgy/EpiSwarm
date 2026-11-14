import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Settings as SettingsIcon, Cpu, CheckCircle2, XCircle, AlertTriangle, Key, Server, RefreshCw } from 'lucide-react';

export const Settings: React.FC = () => {
  const { data: health, refetch: refetchHealth } = useQuery({ queryKey: ['health'], queryFn: api.getHealth });
  const { data: backends, isLoading, refetch: refetchBackends } = useQuery({ queryKey: ['backends'], queryFn: api.getBackends });

  const handleRefresh = () => {
    refetchHealth();
    refetchBackends();
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">System Infrastructure & Backends</h1>
          <p className="text-sm text-slate-500 mt-1">
            Simulation compute engines, persistent database queues, and LLM reasoning integrations.
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Refresh Status
        </button>
      </div>

      {/* Operational Health Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            <div>
              <h3 className="font-bold text-slate-900 text-sm">EpiSwarm API Service: {health?.status.toUpperCase() || 'OK'}</h3>
              <p className="text-xs text-slate-500">Service: {health?.service} · Version: {health?.version}</p>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-mono">{health?.timestamp}</span>
        </div>
      </div>

      {/* Backend Engines Inventory */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-600" />
            Registered Simulation & AI Reasoning Backends
          </h3>
          <span className="text-xs text-slate-500">Credentials masked per security guidelines</span>
        </div>

        <div className="divide-y divide-slate-100">
          {isLoading ? (
            <div className="p-8 text-center text-slate-400">Inspecting backend status...</div>
          ) : backends?.backends.map((b) => (
            <div key={b.name} className="p-5 flex flex-wrap items-center justify-between gap-4 hover:bg-slate-50">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 text-sm">{b.name}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    b.status === 'available' ? 'bg-emerald-100 text-emerald-800' : (b.configured ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-600')
                  }`}>
                    {b.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs text-slate-600">
                  {b.details?.provider || 'Native Subsystem'} {b.active_model && `· Model: ${b.active_model}`}
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs">
                {b.configured ? (
                  <span className="text-emerald-700 flex items-center gap-1 font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Configured
                  </span>
                ) : (
                  <span className="text-slate-400 flex items-center gap-1">
                    <XCircle className="w-4 h-4 text-slate-300" /> Not Provided
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

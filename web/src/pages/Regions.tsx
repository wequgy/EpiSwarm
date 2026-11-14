import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import { RegionSummary, PackValidationResult } from '../api/types';
import { Layers, CheckCircle2, XCircle, AlertCircle, RefreshCw, FileText, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Regions: React.FC = () => {
  const { data: regions, isLoading, refetch } = useQuery({
    queryKey: ['regions'],
    queryFn: api.getRegions,
  });

  const [validationResult, setValidationResult] = useState<PackValidationResult | null>(null);

  const validateMutation = useMutation({
    mutationFn: (regionId: string) => api.validateRegion(regionId),
    onSuccess: (data) => setValidationResult(data),
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Regions & Administrative Topology</h1>
          <p className="text-sm text-slate-500 mt-1">
            Demographic structures, commute origin-destination flows, and hospital catchments.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Refresh
          </button>
          <Link
            to="/builder"
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" /> Quick Region Builder
          </Link>
        </div>
      </div>

      {/* Validation Result Modal / Notification Banner */}
      {validationResult && (
        <div className={`p-4 rounded-xl border ${
          validationResult.is_valid ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-rose-50 border-rose-200 text-rose-900'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold text-sm">
              {validationResult.is_valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : (
                <XCircle className="w-5 h-5 text-rose-600" />
              )}
              Validation Contract: {validationResult.pack_id} ({validationResult.is_valid ? 'PASSED' : 'FAILED'})
            </div>
            <button onClick={() => setValidationResult(null)} className="text-xs font-bold text-slate-400 hover:text-slate-600">✕</button>
          </div>
          {validationResult.errors.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs list-disc pl-5">
              {validationResult.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Grid of Regions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-3 text-center py-12 text-slate-400">Loading regions...</div>
        ) : regions?.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 uppercase">
                  {r.data_level || 'L0 Quick'}
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                  r.provenance_status === 'REAL' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
                }`}>
                  {r.provenance_status}
                </span>
              </div>

              <h3 className="text-lg font-bold text-slate-900">{r.name}</h3>
              <p className="text-xs text-slate-500 font-mono mt-0.5">ID: {r.id}</p>

              {r.notes && (
                <p className="text-xs text-slate-600 mt-2 line-clamp-2 italic">{r.notes}</p>
              )}

              {/* Specs */}
              <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Population</span>
                  <span className="font-semibold text-slate-800">
                    {r.total_population ? r.total_population.toLocaleString() : 'Synthesized'}
                  </span>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Admin Areas</span>
                  <span className="font-semibold text-slate-800">{r.num_areas || 'Dynamic'}</span>
                </div>
              </div>

              {/* Table Files Inventory */}
              <div className="mt-4 border-t border-slate-100 pt-3">
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1.5">Table Artifacts</span>
                <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                  <span className={`flex items-center gap-1 ${r.areas_file_exists ? 'text-slate-700' : 'text-slate-400'}`}>
                    {r.areas_file_exists ? <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                    areas.csv
                  </span>
                  <span className={`flex items-center gap-1 ${r.contacts_file_exists ? 'text-slate-700' : 'text-slate-400'}`}>
                    {r.contacts_file_exists ? <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                    contacts.csv
                  </span>
                  <span className={`flex items-center gap-1 ${r.commute_file_exists ? 'text-slate-700' : 'text-slate-400'}`}>
                    {r.commute_file_exists ? <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                    commute_od.csv
                  </span>
                  <span className={`flex items-center gap-1 ${r.observed_cases_exists ? 'text-slate-700' : 'text-slate-400'}`}>
                    {r.observed_cases_exists ? <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                    observed_cases.csv
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={() => validateMutation.mutate(r.id)}
                disabled={validateMutation.isPending}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                Validate Pack Contract →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

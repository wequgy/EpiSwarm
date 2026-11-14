import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import { BehaviorSummary, PackValidationResult } from '../api/types';
import { Users, CheckCircle2, XCircle, RefreshCw, MessageSquare } from 'lucide-react';

export const Behaviors: React.FC = () => {
  const { data: behaviors, isLoading, refetch } = useQuery({
    queryKey: ['behaviors'],
    queryFn: api.getBehaviors,
  });

  const [validationResult, setValidationResult] = useState<PackValidationResult | null>(null);

  const validateMutation = useMutation({
    mutationFn: (behaviorId: string) => api.validateBehavior(behaviorId),
    onSuccess: (data) => setValidationResult(data),
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Behavior & Compliance Packs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Psychographic compliance weights, decision questions, and misinformation dynamics.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Refresh
        </button>
      </div>

      {validationResult && (
        <div className={`p-4 rounded-xl border ${
          validationResult.is_valid ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-rose-50 border-rose-200 text-rose-900'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold text-sm">
              {validationResult.is_valid ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <XCircle className="w-5 h-5 text-rose-600" />}
              Behavior Pack Validation: {validationResult.pack_id} ({validationResult.is_valid ? 'PASSED' : 'FAILED'})
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-3 text-center py-12 text-slate-400">Loading behavior packs...</div>
        ) : behaviors?.map((b) => (
          <div key={b.id} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 uppercase">
                  {b.n_questions} Questions
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-100 text-red-800">
                  {b.n_rumor_topics} Rumor Topics
                </span>
              </div>

              <h3 className="text-lg font-bold text-slate-900">{b.name}</h3>
              <p className="text-xs text-slate-500 font-mono mt-0.5">ID: {b.id}</p>

              {b.context && (
                <p className="text-xs text-slate-600 mt-2 line-clamp-2 italic">{b.context}</p>
              )}

              <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Spread Rate</span>
                  <span className="font-semibold text-slate-800">{b.rumor_spread_rate || 0.05}</span>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Decision Prompts</span>
                  <span className="font-semibold text-slate-800">{b.n_questions} Active</span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={() => validateMutation.mutate(b.id)}
                disabled={validateMutation.isPending}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                Validate Psychographics →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { TrustBadge } from '../components/TrustBadge';
import { FileCheck2, ShieldAlert, CheckCircle2, XCircle, AlertTriangle, FileCode } from 'lucide-react';

export const Validation: React.FC = () => {
  const { data: card } = useQuery({ queryKey: ['validationCard'], queryFn: api.getValidationCard });
  const { data: report } = useQuery({ queryKey: ['validationReport'], queryFn: api.getValidationReport });
  const { data: assumptions } = useQuery({ queryKey: ['assumptions'], queryFn: api.getAssumptions });

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Empirical Validation & Benchmark Transparency</h1>
          <p className="text-sm text-slate-500 mt-1">
            Pre-registered benchmark target compliance, audit trail findings, and assumptions register.
          </p>
        </div>
        <TrustBadge status={card?.status} size="lg" />
      </div>

      {/* Target Compliance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Registered Deaths */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400">Target 1</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800">IN-SAMPLE</span>
          </div>
          <h4 className="font-bold text-slate-900 text-sm">Registered Deaths</h4>
          <p className="text-xs text-slate-600">Peak day error: 0 days · Ratio: 1.0 (0.37% error)</p>
          <div className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Satisfied (Calibration Fit)
          </div>
        </div>

        {/* Spatial Arrival Order */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400">Target 2</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800">FAILED</span>
          </div>
          <h4 className="font-bold text-slate-900 text-sm">Spatial Arrival Order</h4>
          <p className="text-xs text-slate-600">Rank correlation rho = -0.009 (p=0.96; required &ge; 0.60)</p>
          <div className="text-[10px] text-rose-600 font-semibold flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5" /> Uncalibrated Wavefront
          </div>
        </div>

        {/* Healthcare Overflow */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400">Target 3</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800">FAILED</span>
          </div>
          <h4 className="font-bold text-slate-900 text-sm">Healthcare Overflow</h4>
          <p className="text-xs text-slate-600">Sim peak 9002 vs obs 1057 beds (ratio 8.52; bound [0.75, 1.25])</p>
          <div className="text-[10px] text-rose-600 font-semibold flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5" /> High Bed Demand Overshoot
          </div>
        </div>

        {/* Held-Out Wave 2 */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400">Target 4</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800">COMPROMISED</span>
          </div>
          <h4 className="font-bold text-slate-900 text-sm">Held-Out Wave 2</h4>
          <p className="text-xs text-slate-600">Quarantined per audit finding Y4 (pre-evaluation access breach)</p>
          <div className="text-[10px] text-amber-700 font-semibold flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" /> External Dataset Required
          </div>
        </div>
      </div>

      {/* Assumptions Register Table */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            Active Assumptions Register (Evidence Class C)
          </h3>
          <span className="text-xs text-slate-400">Total: {assumptions?.length || 0} Assumed Defaults</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold text-[10px]">
                <th className="p-3">Parameter Key</th>
                <th className="p-3">Nominal Value</th>
                <th className="p-3">Source & Vintage</th>
                <th className="p-3">Status</th>
                <th className="p-3">Audit Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {assumptions?.map((a) => (
                <tr key={a.parameter} className="hover:bg-slate-50">
                  <td className="p-3 font-mono font-medium text-slate-900">{a.parameter}</td>
                  <td className="p-3 font-semibold text-slate-800">{String(a.value)}</td>
                  <td className="p-3 text-slate-600">{a.source}</td>
                  <td className="p-3">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                      {a.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-500 text-[11px]">{a.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Raw Card JSON Inspector */}
      {card && (
        <div className="bg-slate-950 text-slate-300 rounded-2xl p-6 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-blue-400" /> docs/validation/VALIDATION_CARD.json
            </span>
            <span>Generated: {card.generated_at}</span>
          </div>
          <pre className="text-xs font-mono overflow-x-auto p-4 bg-slate-900 rounded-lg text-emerald-400">
            {JSON.stringify(card, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

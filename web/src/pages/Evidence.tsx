import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Database, ShieldCheck, FileCheck, ExternalLink, Hash, GitCommit } from 'lucide-react';

export const Evidence: React.FC = () => {
  const { data: evidence, isLoading } = useQuery({
    queryKey: ['evidence'],
    queryFn: api.getEvidence,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Cryptographic Evidence Ledger</h1>
          <p className="text-sm text-slate-500 mt-1">
            Immutable, checksummed database of all external empirical data and derived tables (evidence/ledger.db).
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          WAL Authenticated SQLite
        </span>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-600" />
            Verified Datasets & Lineage Records
          </h3>
          <span className="text-xs text-slate-500 font-mono">Total: {evidence?.length || 0} Records</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold text-[10px]">
                <th className="p-3.5">Record ID / Type</th>
                <th className="p-3.5">File & License</th>
                <th className="p-3.5">SHA-256 Digest</th>
                <th className="p-3.5">Bytes</th>
                <th className="p-3.5">Parent Provenance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-400">Loading ledger records...</td>
                </tr>
              ) : (!evidence || evidence.length === 0) ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-400">No evidence records found.</td>
                </tr>
              ) : (
                evidence.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-3.5">
                      <div className="font-mono font-bold text-slate-900 text-[11px]">{rec.id}</div>
                      <span className={`inline-block text-[9px] uppercase font-bold px-1.5 py-0.5 rounded mt-1 ${
                        rec.record_type === 'derived' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {rec.record_type}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <div className="font-semibold text-slate-800">{rec.file_path.split(/[\\/]/).pop()}</div>
                      <div className="text-[10px] text-slate-500">{rec.license} · {rec.content_type}</div>
                    </td>
                    <td className="p-3.5 font-mono text-[10px] text-slate-600 max-w-[160px] truncate" title={rec.sha256}>
                      {rec.sha256}
                    </td>
                    <td className="p-3.5 text-slate-700 font-mono">
                      {(rec.byte_count / 1024).toFixed(1)} KB
                    </td>
                    <td className="p-3.5 text-slate-500 text-[11px]">
                      {rec.record_type === 'derived' ? (
                        <div>
                          <span className="font-semibold text-purple-900 block">
                            {rec.transform_script?.split(/[\\/]/).pop()}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400">
                            Parent Hashes: {rec.parent_ids ? `${JSON.parse(rec.parent_ids).length} inputs` : '—'}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-400">Raw Root Download</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

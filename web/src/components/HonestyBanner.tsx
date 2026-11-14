import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { TrustBadge } from './TrustBadge';
import { AlertTriangle, Database, Activity } from 'lucide-react';

export const HonestyBanner: React.FC = () => {
  const { data: card } = useQuery({
    queryKey: ['validationCard'],
    queryFn: api.getValidationCard,
    staleTime: 60_000,
  });

  const status = card?.status || 'UNCALIBRATED';

  return (
    <div className="bg-white border-b border-slate-200 px-6 py-2.5 flex flex-wrap items-center justify-between gap-4 text-xs">
      <div className="flex items-center gap-3">
        <span className="font-semibold text-slate-700 flex items-center gap-1.5">
          <Activity className="w-4 h-4 text-blue-600" />
          Empirical Validation:
        </span>
        <TrustBadge status={status} size="sm" />
        <span className="text-slate-500 hidden sm:inline">
          {status === 'PARTIALLY_VALIDATED'
            ? 'Calibrated on London Wave 1 (targets 0/3 satisfied; quarantined audits Y1-Y7)'
            : 'Pre-registered benchmarks pending empirical multi-target verification'}
        </span>
      </div>

      <div className="flex items-center gap-4 text-slate-600">
        <span className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          Ledger: <strong className="text-slate-700">SHA-256 Checksummed</strong>
        </span>
        <span className="flex items-center gap-1.5 bg-amber-50 text-amber-800 px-2 py-0.5 rounded border border-amber-200">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          Evidence Class C (Assumed Defaults)
        </span>
      </div>
    </div>
  );
};

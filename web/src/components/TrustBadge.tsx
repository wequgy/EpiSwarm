import React from 'react';
import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react';

interface TrustBadgeProps {
  status?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const TrustBadge: React.FC<TrustBadgeProps> = ({ status = 'UNCALIBRATED', size = 'md' }) => {
  const norm = status.toUpperCase();

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size];

  if (norm.includes('VALIDATED') && !norm.includes('PARTIAL') && !norm.includes('UN')) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 ${sizeClasses}`}>
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
        VALIDATED
      </span>
    );
  }

  if (norm.includes('PARTIALLY')) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold bg-amber-100 text-amber-800 border border-amber-300 ${sizeClasses}`}>
        <Shield className="w-3.5 h-3.5 text-amber-600" />
        PARTIALLY VALIDATED
      </span>
    );
  }

  if (norm.includes('MOCK')) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold bg-indigo-100 text-indigo-800 border border-indigo-300 ${sizeClasses}`}>
        <Shield className="w-3.5 h-3.5 text-indigo-600" />
        MOCK DATA
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold bg-rose-100 text-rose-800 border border-rose-300 ${sizeClasses}`}>
      <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
      UNCALIBRATED
    </span>
  );
};

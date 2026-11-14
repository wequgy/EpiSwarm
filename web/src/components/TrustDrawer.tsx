import React from 'react';
import { Shield, CheckCircle2, AlertTriangle, Database, Cpu, ExternalLink, X, FileText } from 'lucide-react';

interface TrustDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TrustDrawer: React.FC<TrustDrawerProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white border-l border-slate-200 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900">Trust, Data & Provenance</h2>
                <p className="text-xs text-slate-500">Evidence ledger, validation metrics & backend integrity</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Trust Tier Summary */}
            <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">Operational Integrity</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Tier 1: Verified
                </span>
              </div>
              <p className="text-xs text-emerald-900 leading-relaxed">
                Engine outputs adhere strictly to bitwise reproducibility across pause/resume checkpoints. Zero synthetic fabrication in authority modes.
              </p>
            </div>

            {/* Evidence Class Ledger Breakdown */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-400" /> Evidence Hierarchy
              </h3>
              <div className="space-y-2">
                <div className="p-3 rounded-lg border border-slate-200 bg-white shadow-sm flex items-start gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500 mt-1 flex-shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-slate-900">Class A: User Supplied</div>
                    <div className="text-xs text-slate-500">Local authority CSV uploads. Checksummed via SHA-256 and never transmitted off-device.</div>
                  </div>
                </div>
                <div className="p-3 rounded-lg border border-slate-200 bg-white shadow-sm flex items-start gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mt-1 flex-shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-slate-900">Class B: Calibrated / Sourced</div>
                    <div className="text-xs text-slate-500">Empirically fitted using SMC-ABC against public health registry records (PHE, ONS, CDC).</div>
                  </div>
                </div>
                <div className="p-3 rounded-lg border border-slate-200 bg-white shadow-sm flex items-start gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 mt-1 flex-shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-slate-900">Class C: Assumed Defaults</div>
                    <div className="text-xs text-slate-500">Literature-derived priors with cited academic provenance. Require explicit officer sign-off.</div>
                  </div>
                </div>
                <div className="p-3 rounded-lg border border-slate-200 bg-white shadow-sm flex items-start gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-400 mt-1 flex-shrink-0" />
                  <div>
                    <div className="text-xs font-medium text-slate-900">Class D: Synthetic / Demo</div>
                    <div className="text-xs text-slate-500">Rapid test generators. Display persistent prominent MOCK DATA banners.</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Backend & Inference Status */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-slate-400" /> System & Engine Runtime
              </h3>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2 text-xs">
                <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                  <span className="text-slate-600">Vectorized Engine</span>
                  <span className="font-mono text-emerald-600 font-medium">NumPy 64-bit (Bitwise Deterministic)</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                  <span className="text-slate-600">Throughput Target</span>
                  <span className="font-mono text-slate-800">&gt; 50,000 agent-days/sec</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                  <span className="text-slate-600">Local Policy Inference</span>
                  <span className="font-mono text-blue-600 font-medium">Ollama: llama3.2:3b (localhost:11434)</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-slate-600">WebSocket Live Control</span>
                  <span className="font-mono text-emerald-600 font-medium">/api/v2/runs/&#123;id&#125;/live</span>
                </div>
              </div>
            </div>

            {/* Capability Gaps Reference */}
            <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/40 space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-900">
                <FileText className="w-4 h-4 text-blue-600" />
                <span>Engine Scope & Planned Features</span>
              </div>
              <p className="text-xs text-blue-800 leading-relaxed">
                Features not modeled in the vectorized engine core (e.g. genomic mutation drift, longitudinal waning) are never surfaced as deceptive controls.
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
            <span>EpiSwarm Ledger v2</span>
            <span className="font-mono">SHA-256 Immutable</span>
          </div>
        </div>
      </div>
    </div>
  );
};


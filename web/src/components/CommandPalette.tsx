import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Sliders,
  Play,
  FileText,
  BarChart2,
  Shield,
  Layers,
  Hospital,
  GitBranch,
  X,
} from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenTrustDrawer: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onOpenTrustDrawer,
}) => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const items = [
    { label: 'Mode: Case File (Authority Intake)', category: 'Modes', icon: FileText, action: () => navigate('/case-file') },
    { label: 'Mode: Simulate (Live Stage)', category: 'Modes', icon: Play, action: () => navigate('/simulate') },
    { label: 'Mode: Insights & Policy Optimization', category: 'Modes', icon: BarChart2, action: () => navigate('/insights') },
    { label: 'Demo: London Wave 1 Benchmark', category: 'Case Files', icon: Layers, action: () => navigate('/case-file?case=case_london_wave1') },
    { label: 'Demo: Sandbox Mini-City (Fast Tests)', category: 'Case Files', icon: Layers, action: () => navigate('/case-file?case=case_sandbox') },
    { label: 'Insights: Trajectories & Ribbons', category: 'Insights', icon: BarChart2, action: () => navigate('/insights?tab=trajectories') },
    { label: 'Insights: Spatial Diorama & Arrival Times', category: 'Insights', icon: Layers, action: () => navigate('/insights?tab=spatial') },
    { label: 'Insights: Hospital & ICU Bed Demand', category: 'Insights', icon: Hospital, action: () => navigate('/insights?tab=capacity') },
    { label: 'Insights: Vulnerability & Demographic Equity', category: 'Insights', icon: BarChart2, action: () => navigate('/insights?tab=equity') },
    { label: 'Insights: Counterfactual Compare & Branching', category: 'Insights', icon: GitBranch, action: () => navigate('/insights?tab=compare') },
    { label: 'Insights: Pareto Frontier & Optimization', category: 'Insights', icon: Sliders, action: () => navigate('/insights?tab=pareto') },
    { label: 'Insights: AI Policy Advisor Chat', category: 'Insights', icon: FileText, action: () => navigate('/insights?tab=advisor') },
    { label: 'Insights: Calibration Studio (SMC-ABC)', category: 'Insights', icon: Sliders, action: () => navigate('/insights?tab=calibration') },
    { label: 'Trust & Data: Empirical Validation & Ledger', category: 'Trust & Data', icon: Shield, action: () => { onClose(); onOpenTrustDrawer(); } },
  ];

  const filtered = items.filter(i =>
    i.label.toLowerCase().includes(query.toLowerCase()) ||
    i.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="flex items-center px-4 py-3 border-b border-slate-200 bg-slate-50/50">
          <Search className="w-5 h-5 text-slate-400 mr-3" />
          <input
            type="text"
            className="flex-1 bg-transparent text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none"
            placeholder="Search views, parameters, demos, or actions (Ctrl+K)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-96 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-500">
              No results found for "{query}".
            </div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon;
              return (
                <button
                  key={idx}
                  onClick={() => {
                    item.action();
                    onClose();
                  }}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left hover:bg-blue-50/70 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-md bg-slate-100 text-slate-600 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-900 group-hover:text-blue-900">{item.label}</div>
                      <div className="text-xs text-slate-400">{item.category}</div>
                    </div>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">Jump ↵</span>
                </button>
              );
            })
          )}
        </div>

        <div className="px-4 py-2 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <span>Tip: Press <kbd className="px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded font-mono">Esc</kbd> to exit</span>
          <span className="text-blue-600 font-medium">EpiSwarm Studio v2</span>
        </div>
      </div>
    </div>
  );
};


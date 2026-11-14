import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  FileText,
  Play,
  BarChart3,
  Search,
  Shield,
  Layers,
  Sparkles,
  Command,
} from 'lucide-react';

interface TopBarProps {
  onOpenCommandPalette: () => void;
  onOpenTrustDrawer: () => void;
  trustTier?: string;
  isDemo?: boolean;
  demoLabel?: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  onOpenCommandPalette,
  onOpenTrustDrawer,
  trustTier = 'Tier 1: Calibrated',
  isDemo = true,
  demoLabel = 'DEMO: London Wave 1',
}) => {
  const location = useLocation();

  const navLinks = [
    { to: '/case-file', label: 'Case File', icon: FileText, desc: 'Intake & Boundaries' },
    { to: '/simulate', label: 'Simulate', icon: Play, desc: 'Live Canvas Stage' },
    { to: '/insights', label: 'Insights', icon: BarChart3, desc: 'Outcomes & Advisor' },
  ];

  return (
    <header className="h-16 bg-white/90 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-40 px-6 flex items-center justify-between transition-all">
      {/* Brand & Studio Title */}
      <div className="flex items-center gap-6">
        <NavLink to="/case-file" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 tracking-tight text-sm">EpiSwarm Studio</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200/60">v2</span>
            </div>
            <div className="text-[11px] text-slate-400 font-medium">Authority Simulation Workbench</div>
          </div>
        </NavLink>

        {/* 3 Main Modes Navigation */}
        <nav className="flex items-center p-1 bg-slate-100/80 rounded-xl border border-slate-200/60 gap-1">
          {navLinks.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.to) || (item.to === '/case-file' && location.pathname === '/');
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-white text-blue-600 shadow-sm shadow-slate-200/50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Badges, Command Palette, and Trust Drawer Button */}
      <div className="flex items-center gap-3">
        {/* Demo Mode Badge */}
        {isDemo ? (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300 shadow-xs animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5" />
            {demoLabel}
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mr-1.5" />
            Authority Case File
          </span>
        )}

        {/* Trust Tier Badge */}
        <button
          onClick={onOpenTrustDrawer}
          className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors cursor-pointer"
          title="Click to view Validation and Provenance Ledger"
        >
          <Shield className="w-3.5 h-3.5 mr-1 text-emerald-600" />
          {trustTier}
        </button>

        {/* Command Palette Trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200/80 bg-slate-50 text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors text-xs font-medium shadow-2xs"
          title="Quick search (Ctrl+K)"
        >
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span>Search</span>
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-white border border-slate-200 rounded text-slate-500">
            Ctrl+K
          </kbd>
        </button>

        {/* Trust Drawer Toggle */}
        <button
          onClick={onOpenTrustDrawer}
          className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          title="Open Trust and Data Ledger"
        >
          <Shield className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};


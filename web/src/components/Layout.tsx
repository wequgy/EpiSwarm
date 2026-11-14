import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Activity,
  Layers,
  Bug,
  Sliders,
  Play,
  BarChart3,
  Hospital,
  Map,
  Scale,
  Users,
  GitCompare,
  TrendingUp,
  Bot,
  FileCheck2,
  Database,
  Settings,
  FolderPlus,
} from 'lucide-react';
import { HonestyBanner } from './HonestyBanner';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navSections: Array<{ title: string; items: NavItem[] }> = [
  {
    title: 'Core Platform',
    items: [
      { to: '/', label: 'Studio Home', icon: Activity },
      { to: '/runs', label: 'Simulation Runs', icon: Play },
    ],
  },
  {
    title: 'Model Packs',
    items: [
      { to: '/regions', label: 'Regions & Demographics', icon: Layers },
      { to: '/diseases', label: 'Pathogens & State Graph', icon: Bug },
      { to: '/scenarios', label: 'Intervention Scenarios', icon: Sliders },
      { to: '/behaviors', label: 'Behavior & Compliance', icon: Users },
      { to: '/builder', label: 'Quick Region & Import', icon: FolderPlus },
    ],
  },
  {
    title: 'Analysis & Outcomes',
    items: [
      { to: '/capacity', label: 'Healthcare & Bed Demand', icon: Hospital },
      { to: '/spatial', label: 'Spatial Diorama', icon: Map },
      { to: '/equity', label: 'Vulnerability & Equity', icon: Scale },
      { to: '/behavior-analysis', label: 'Rumors & Compliance', icon: Users },
    ],
  },
  {
    title: 'Advisory & Optimization',
    items: [
      { to: '/compare', label: 'Counterfactual Compare', icon: GitCompare },
      { to: '/optimization', label: 'Marginal Value & Pareto', icon: TrendingUp },
      { to: '/advisor', label: 'Policy Advisor Chat', icon: Bot },
    ],
  },
  {
    title: 'Trust & Governance',
    items: [
      { to: '/validation', label: 'Validation Card & Report', icon: FileCheck2 },
      { to: '/evidence', label: 'Evidence Ledger', icon: Database },
      { to: '/settings', label: 'System & Backends', icon: Settings },
    ],
  },
];

export const Layout: React.FC = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800">
        {/* Brand */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow">
            🧬
          </div>
          <div>
            <h1 className="font-bold text-white text-base tracking-tight leading-none">EpiSwarm Studio</h1>
            <p className="text-[10px] text-slate-400 mt-1 uppercase tracking-wider font-semibold">Decoupled Web Platform</p>
          </div>
        </div>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
          {navSections.map((sec) => (
            <div key={sec.title}>
              <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {sec.title}
              </div>
              <nav className="space-y-1">
                {sec.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                        isActive
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                      }`}
                    >
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* Bottom indicator */}
        <div className="p-4 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            API v1 Connected
          </span>
          <span className="font-mono text-slate-400">v1.0.0</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <HonestyBanner />
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { CommandPalette } from './CommandPalette';
import { TrustDrawer } from './TrustDrawer';

export const Layout: React.FC = () => {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isTrustDrawerOpen, setIsTrustDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900 selection:bg-blue-100 selection:text-blue-900 antialiased font-sans">
      {/* Top Bar with 3 Modes and Global Status */}
      <TopBar
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onOpenTrustDrawer={() => setIsTrustDrawerOpen(true)}
        trustTier="Tier 1: Calibrated"
        isDemo={true}
        demoLabel="DEMO: London Wave 1"
      />

      {/* Main Canvas Area */}
      <main className="flex-1 flex flex-col relative w-full overflow-x-hidden">
        <Outlet />
      </main>

      {/* Global Cmd+K Search Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onOpenTrustDrawer={() => setIsTrustDrawerOpen(true)}
      />

      {/* Global Trust & Data Slide-over Drawer */}
      <TrustDrawer
        isOpen={isTrustDrawerOpen}
        onClose={() => setIsTrustDrawerOpen(false)}
      />
    </div>
  );
};

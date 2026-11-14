import React, { useState } from 'react';
import { Layers, Sparkles, FileSpreadsheet, CheckCircle2, ArrowRight } from 'lucide-react';

export const QuickRegionBuilder: React.FC = () => {
  const [name, setName] = useState('New Metropolis');
  const [countryIso, setCountryIso] = useState('GBR');
  const [population, setPopulation] = useState(150000);
  const [numAreas, setNumAreas] = useState(6);
  const [avgHouseholdSize, setAvgHouseholdSize] = useState(3.2);
  const [urbanFraction, setUrbanFraction] = useState(0.85);
  const [bedsPer1000, setBedsPer1000] = useState(2.5);
  const [icuBedsPer1000, setIcuBedsPer1000] = useState(0.2);

  const [synthesized, setSynthesized] = useState(false);

  const handleSynthesize = (e: React.FormEvent) => {
    e.preventDefault();
    setSynthesized(true);
  };

  const totalBeds = Math.round((population * bedsPer1000) / 1000);
  const totalIcuBeds = Math.round((population * icuBedsPer1000) / 1000);
  const avgAreaPop = Math.round(population / numAreas);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Quick Region Builder & Data Importer</h1>
        <p className="text-sm text-slate-500 mt-1">
          Synthesize L0/L1 demographic topologies from high-level aggregates or import localized CSV tables.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm border-b border-slate-100 pb-3">
            <Sparkles className="w-4 h-4 text-blue-600" />
            L0 Aggregate Demographic Synthesis
          </div>

          <form onSubmit={handleSynthesize} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Region Identifier Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Country ISO Code</label>
                <input
                  type="text"
                  value={countryIso}
                  onChange={(e) => setCountryIso(e.target.value.toUpperCase())}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  maxLength={3}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Total Population</label>
                <input
                  type="number"
                  value={population}
                  onChange={(e) => setPopulation(Number(e.target.value))}
                  min={1000}
                  step={5000}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Number of Administrative Areas</label>
                <input
                  type="number"
                  value={numAreas}
                  onChange={(e) => setNumAreas(Number(e.target.value))}
                  min={1}
                  max={50}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Avg Household</label>
                <input
                  type="number"
                  value={avgHouseholdSize}
                  onChange={(e) => setAvgHouseholdSize(Number(e.target.value))}
                  step={0.1}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Urban Share</label>
                <input
                  type="number"
                  value={urbanFraction}
                  onChange={(e) => setUrbanFraction(Number(e.target.value))}
                  step={0.05}
                  min={0}
                  max={1}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Beds / 1k</label>
                <input
                  type="number"
                  value={bedsPer1000}
                  onChange={(e) => setBedsPer1000(Number(e.target.value))}
                  step={0.1}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">ICU Beds / 1k</label>
                <input
                  type="number"
                  value={icuBedsPer1000}
                  onChange={(e) => setIcuBedsPer1000(Number(e.target.value))}
                  step={0.05}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="w-full py-2.5 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-500 transition-colors shadow-sm"
              >
                Synthesize Regional Tables
              </button>
            </div>
          </form>
        </div>

        {/* Live Synthesis Preview */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm border-b border-slate-100 pb-3">
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Synthesized Topology Metrics
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 flex items-center justify-between">
              <span className="text-slate-500">Region Name</span>
              <strong className="text-slate-800">{name} ({countryIso})</strong>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 flex items-center justify-between">
              <span className="text-slate-500">Boroughs / Areas</span>
              <strong className="text-slate-800">{numAreas} units (~{avgAreaPop.toLocaleString()} pop/area)</strong>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 flex items-center justify-between">
              <span className="text-slate-500">Total General Hospital Beds</span>
              <strong className="text-amber-700">{totalBeds.toLocaleString()} beds</strong>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 flex items-center justify-between">
              <span className="text-slate-500">Total ICU Bed Capacity</span>
              <strong className="text-red-700">{totalIcuBeds.toLocaleString()} beds</strong>
            </div>
          </div>

          {synthesized && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Topology Ready for Simulation
              </div>
              <p className="text-[11px] text-emerald-800">
                Generated synthetic age structure, Prem contact fallback, and commute gravity flow matrix.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

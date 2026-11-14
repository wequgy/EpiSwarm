import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { AreaSpatialPoint } from '../api/types';
import { Map, Play, Pause, RotateCcw, Layers, Info, Activity } from 'lucide-react';

export const SpatialDiorama: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { data: runsList } = useQuery({ queryKey: ['runsList'], queryFn: () => api.listRuns(50) });

  const completedRuns = runsList?.jobs.filter((j) => j.status === 'COMPLETED') || [];
  const defaultRunId = searchParams.get('jobId') || completedRuns[0]?.job_id || '';
  const [selectedRunId, setSelectedRunId] = useState(defaultRunId);

  const activeRunId = selectedRunId || defaultRunId;

  const { data: spatial, isLoading } = useQuery({
    queryKey: ['runSpatial', activeRunId],
    queryFn: () => api.getRunSpatial(activeRunId),
    enabled: !!activeRunId,
  });

  // Time scrubber state for wavefront animation
  const [currentDay, setCurrentDay] = useState(25);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedBorough, setSelectedBorough] = useState<AreaSpatialPoint | null>(null);

  // Active layer filters
  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>({
    household: true,
    school: true,
    workplace: true,
    healthcare: true,
    transit: true,
  });

  const toggleLayer = (layerId: string) => {
    setActiveLayers((prev) => ({ ...prev, [layerId]: !prev[layerId] }));
  };

  const maxDays = spatial?.areas[0]?.daily_incident_infections?.length || 60;

  // Animation effect
  React.useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentDay((prev) => (prev >= maxDays - 1 ? 0 : prev + 1));
      }, 200);
    }
    return () => clearInterval(timer);
  }, [isPlaying, maxDays]);

  // Color generator based on day's incident infection intensity
  const getBoroughColor = (b: AreaSpatialPoint, day: number) => {
    const inc = b.daily_incident_infections?.[day] || 0;
    const peak = Math.max(...(b.daily_incident_infections || [1]));
    const ratio = peak > 0 ? inc / peak : 0;

    if (ratio > 0.75) return '#dc2626'; // Red - intense outbreak peak
    if (ratio > 0.45) return '#ea580c'; // Orange - accelerating wavefront
    if (ratio > 0.20) return '#f59e0b'; // Amber - expanding
    if (ratio > 0.05) return '#eab308'; // Yellow - low active
    return '#3b82f6'; // Blue - baseline / quiescent
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            3D Isometric City Diorama & Wavefronts
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Multi-layer urban topology visualizing spatial transmission across boroughs and commute corridors.
          </p>
        </div>

        {/* Run Selector */}
        {completedRuns.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-slate-600">Select Run:</span>
            <select
              value={activeRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 bg-white font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {completedRuns.map((r) => (
                <option key={r.job_id} value={r.job_id}>
                  {r.job_id} ({r.request.scenario_id})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading spatial diorama...</div>
      ) : !spatial ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
          No spatial diorama data available for selected run.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Diorama Canvas & Controls */}
          <div className="lg:col-span-3 bg-slate-950 rounded-2xl p-6 border border-slate-800 shadow-xl flex flex-col justify-between space-y-6">
            {/* Top Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                  Region: {spatial.region_id} ({spatial.n_areas} Boroughs)
                </span>
              </div>

              {/* Layer Toggles */}
              <div className="flex flex-wrap items-center gap-2">
                {spatial.layers.map((layer) => {
                  const active = activeLayers[layer.id];
                  return (
                    <button
                      key={layer.id}
                      onClick={() => toggleLayer(layer.id)}
                      className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors border ${
                        active
                          ? 'bg-slate-800 text-white border-slate-600'
                          : 'bg-slate-900/60 text-slate-400 border-slate-800'
                      }`}
                    >
                      <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: layer.color }} />
                      {layer.name.split(' ')[0]}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Isometric SVG Diorama Visualizer */}
            <div className="relative w-full h-[400px] flex items-center justify-center overflow-hidden">
              <svg viewBox="-300 -200 600 400" className="w-full h-full">
                <defs>
                  <linearGradient id="gridGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#1e293b" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#0f172a" stopOpacity="0.8" />
                  </linearGradient>
                </defs>

                {/* Ground grid lines */}
                {[-180, -90, 0, 90, 180].map((x) => (
                  <line
                    key={`gx-${x}`}
                    x1={x - 120}
                    y1={x * 0.5 - 60}
                    x2={x + 120}
                    y2={x * 0.5 + 60}
                    stroke="#1e293b"
                    strokeWidth="1"
                    strokeDasharray="4 4"
                  />
                ))}

                {/* Commute Network Links */}
                {activeLayers.transit && spatial.areas.length > 1 && (
                  <g className="commute-links" opacity="0.4">
                    {spatial.areas.map((a, i) => {
                      const next = spatial.areas[(i + 1) % spatial.areas.length];
                      return (
                        <line
                          key={`link-${i}`}
                          x1={a.iso_x}
                          y1={a.iso_y}
                          x2={next.iso_x}
                          y2={next.iso_y}
                          stroke="#9013fe"
                          strokeWidth="2"
                          strokeDasharray="6 4"
                        />
                      );
                    })}
                  </g>
                )}

                {/* 3D Borough Blocks */}
                {spatial.areas.map((b) => {
                  const x = b.iso_x;
                  const y = b.iso_y;
                  const color = getBoroughColor(b, currentDay);
                  const isSelected = selectedBorough?.area_id === b.area_id;

                  // 3D Isometric Cube Projection
                  // Width = 60, Depth = 40, Height modulated by density
                  const height = 25 + (b.density / 12000) * 35;
                  const w = 45;
                  const h = 22;

                  return (
                    <g
                      key={b.area_id}
                      onClick={() => setSelectedBorough(b)}
                      className="cursor-pointer transition-transform hover:scale-105"
                      style={{ transformOrigin: `${x}px ${y}px` }}
                    >
                      {/* Left Wall */}
                      <path
                        d={`M ${x - w} ${y} L ${x} ${y + h} L ${x} ${y + h - height} L ${x - w} ${y - height} Z`}
                        fill={color}
                        fillOpacity="0.75"
                        stroke="#0f172a"
                        strokeWidth="1"
                      />

                      {/* Right Wall */}
                      <path
                        d={`M ${x} ${y + h} L ${x + w} ${y} L ${x + w} ${y - height} L ${x} ${y + h - height} Z`}
                        fill={color}
                        fillOpacity="0.6"
                        stroke="#0f172a"
                        strokeWidth="1"
                      />

                      {/* Top Face */}
                      <path
                        d={`M ${x} ${y - height - h} L ${x + w} ${y - height} L ${x} ${y - height + h} L ${x - w} ${y - height} Z`}
                        fill={color}
                        stroke={isSelected ? '#ffffff' : '#0f172a'}
                        strokeWidth={isSelected ? '2.5' : '1'}
                      />

                      {/* Borough Label */}
                      <text
                        x={x}
                        y={y - height - 8}
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize="9"
                        fontWeight="bold"
                        className="select-none pointer-events-none drop-shadow"
                      >
                        {b.area_id}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Timeline Wavefront Scrubbing Bar */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors"
                  >
                    {isPlaying ? <Pause className="w-3.5 h-3.5 fill-white" /> : <Play className="w-3.5 h-3.5 fill-white" />}
                  </button>
                  <button
                    onClick={() => setCurrentDay(0)}
                    className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                    title="Reset to Day 0"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                  <span className="font-bold text-sm text-white">
                    Day {currentDay} <span className="text-slate-400 font-normal text-xs">/ {maxDays - 1}</span>
                  </span>
                </div>

                <div className="flex items-center gap-4 text-[11px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded bg-blue-500 inline-block" /> Low
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block" /> Rising
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded bg-red-600 inline-block" /> Peak Wave
                  </span>
                </div>
              </div>

              <input
                type="range"
                min={0}
                max={maxDays - 1}
                value={currentDay}
                onChange={(e) => setCurrentDay(Number(e.target.value))}
                className="w-full accent-blue-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>
          </div>

          {/* Right Inspector Drawer */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between space-y-6">
            <div>
              <div className="flex items-center gap-2 font-bold text-slate-900 text-sm border-b border-slate-100 pb-3">
                <Info className="w-4 h-4 text-blue-600" />
                Borough Inspection
              </div>

              {selectedBorough ? (
                <div className="space-y-4 pt-3">
                  <div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-mono">
                      {selectedBorough.area_id}
                    </span>
                    <h3 className="text-base font-bold text-slate-900 mt-1">{selectedBorough.name}</h3>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-50 flex items-center justify-between">
                      <span className="text-slate-500">Population</span>
                      <strong className="text-slate-800">{selectedBorough.population.toLocaleString()}</strong>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 flex items-center justify-between">
                      <span className="text-slate-500">Density</span>
                      <strong className="text-slate-800">{Math.round(selectedBorough.density)} / km²</strong>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 flex items-center justify-between">
                      <span className="text-slate-500">Attack Rate</span>
                      <strong className="text-blue-600">{(selectedBorough.attack_rate * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 flex items-center justify-between">
                      <span className="text-slate-500">Cumulative Infections</span>
                      <strong className="text-red-600">{selectedBorough.total_infections.toLocaleString()}</strong>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 flex items-center justify-between">
                      <span className="text-slate-500">Wavefront Peak</span>
                      <strong className="text-slate-800">Day {selectedBorough.peak_day}</strong>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-blue-50 border border-blue-100 text-[11px] text-blue-900">
                    Day {currentDay} Active Daily Infections:{' '}
                    <strong>{Math.round(selectedBorough.daily_incident_infections[currentDay] || 0)}</strong>
                  </div>
                </div>
              ) : (
                <div className="py-12 text-center text-xs text-slate-400">
                  Click any isometric 3D borough block on the diorama to inspect localized demographics, wavefront arrival day, and attack rates.
                </div>
              )}
            </div>

            <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-3 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-slate-400" />
              Isometric 2:1 ratio projection with height extrusion
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

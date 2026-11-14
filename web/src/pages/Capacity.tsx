import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import ReactECharts from 'echarts-for-react';
import { Hospital } from 'lucide-react';

export const Capacity: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { data: runsList } = useQuery({ queryKey: ['runsList'], queryFn: () => api.listRuns(50) });

  const completedRuns = runsList?.jobs.filter((j) => j.status === 'COMPLETED') || [];
  const defaultRunId = searchParams.get('jobId') || completedRuns[0]?.job_id || '';
  const [selectedRunId, setSelectedRunId] = useState(defaultRunId);

  const activeRunId = selectedRunId || defaultRunId;

  const { data: capacity, isLoading } = useQuery({
    queryKey: ['runCapacity', activeRunId],
    queryFn: () => api.getRunCapacity(activeRunId),
    enabled: !!activeRunId,
  });

  const days = capacity ? Array.from({ length: capacity.daily_hospital_demand.length }, (_, i) => `Day ${i}`) : [];

  const chartOption = capacity ? {
    title: { text: 'Hospital Bed Occupancy vs Physical Capacity Limit', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold' } },
    tooltip: { trigger: 'axis' },
    legend: { top: 'bottom', data: ['Hospital Bed Demand', 'Hospital Capacity Threshold', 'ICU Demand', 'ICU Capacity Threshold'] },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: days, boundaryGap: false },
    yAxis: { type: 'value', name: 'Beds' },
    series: [
      {
        name: 'Hospital Bed Demand',
        type: 'line',
        smooth: true,
        data: capacity.daily_hospital_demand,
        color: '#f59e0b',
        showSymbol: false,
        areaStyle: {
          opacity: 0.1,
        },
      },
      {
        name: 'Hospital Capacity Threshold',
        type: 'line',
        data: Array(days.length).fill(capacity.hospital_capacity_beds),
        color: '#d97706',
        lineStyle: { type: 'dashed', width: 2 },
        showSymbol: false,
      },
      {
        name: 'ICU Demand',
        type: 'line',
        smooth: true,
        data: capacity.daily_icu_demand,
        color: '#ef4444',
        showSymbol: false,
      },
      {
        name: 'ICU Capacity Threshold',
        type: 'line',
        data: Array(days.length).fill(capacity.icu_capacity_beds),
        color: '#b91c1c',
        lineStyle: { type: 'dashed', width: 2 },
        showSymbol: false,
      },
    ],
  } : {};

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Healthcare Capacity & Bed Occupancy</h1>
          <p className="text-sm text-slate-500 mt-1">
            Acute inpatient demand, ICU triage saturation, and overflow-attributable mortality.
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
        <div className="p-12 text-center text-slate-400">Loading capacity metrics...</div>
      ) : !capacity ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
          No capacity data available for selected run. Run a simulation first!
        </div>
      ) : (
        <>
          {/* Key Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Hospital Baseline Beds</span>
              <div className="text-2xl font-extrabold text-slate-900 mt-1">
                {Math.round(capacity.hospital_capacity_beds).toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500">General acute care beds</span>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">ICU Beds Limit</span>
              <div className="text-2xl font-extrabold text-slate-900 mt-1">
                {Math.round(capacity.icu_capacity_beds).toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500">Intensive respiratory beds</span>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <span className="text-[10px] uppercase font-bold text-amber-500 block tracking-wider">Hospital Overflow Days</span>
              <div className="text-2xl font-extrabold text-amber-600 mt-1">
                {capacity.overflow_days_hospital} Days
              </div>
              <span className="text-[10px] text-amber-700">Days demand exceeded capacity</span>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <span className="text-[10px] uppercase font-bold text-red-500 block tracking-wider">ICU Overflow Days</span>
              <div className="text-2xl font-extrabold text-red-600 mt-1">
                {capacity.overflow_days_icu} Days
              </div>
              <span className="text-[10px] text-red-700">Critical care triage duration</span>
            </div>
          </div>

          {/* Capacity Utilization Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <ReactECharts option={chartOption} style={{ height: '380px', width: '100%' }} />
          </div>
        </>
      )}
    </div>
  );
};

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { RunCreateRequest, JobRecord, JobStatus } from '../api/types';
import { Play, RotateCcw, AlertTriangle, CheckCircle2, Clock, Ban, Eye, Sparkles } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export const Runs: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: regions } = useQuery({ queryKey: ['regions'], queryFn: api.getRegions });
  const { data: diseases } = useQuery({ queryKey: ['diseases'], queryFn: api.getDiseases });
  const { data: scenarios } = useQuery({ queryKey: ['scenarios'], queryFn: api.getScenarios });
  const { data: backends } = useQuery({ queryKey: ['backends'], queryFn: api.getBackends });

  const localBackend = backends?.backends?.find((b) => b.name === 'local_llm');

  const { data: jobsList, refetch: refetchJobs } = useQuery({
    queryKey: ['runsList'],
    queryFn: () => api.listRuns(50),
    refetchInterval: 3000,
  });

  // Launch Form State
  const [regionId, setRegionId] = useState('example_synthetic');
  const [diseaseId, setDiseaseId] = useState('respiratory_generic');
  const [scenarioId, setScenarioId] = useState('targeted_containment');
  const [scaleAgents, setScaleAgents] = useState(3000);
  const [behaviorMode, setBehaviorMode] = useState<'none' | 'rule' | 'llm'>('rule');
  const [nReplicates, setNReplicates] = useState(3);
  const [horizonDays, setHorizonDays] = useState(60);
  const [useMock, setUseMock] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const launchMutation = useMutation({
    mutationFn: (req: RunCreateRequest) => api.launchRun(req),
    onSuccess: (job: JobRecord) => {
      queryClient.invalidateQueries({ queryKey: ['runsList'] });
      setIsSubmitting(false);
    },
    onError: (err: any) => {
      alert(`Launch error: ${err.message}`);
      setIsSubmitting(false);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => api.cancelRun(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runsList'] });
    },
  });

  const handleLaunch = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    launchMutation.mutate({
      region_id: regionId,
      disease_id: diseaseId,
      scenario_id: scenarioId,
      scale_agents: scaleAgents,
      behavior_mode: behaviorMode,
      n_replicates: nReplicates,
      horizon_days: horizonDays,
      use_mock: useMock,
    });
  };

  const statusBadges: Record<JobStatus, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
    QUEUED: { bg: 'bg-slate-100', text: 'text-slate-700', icon: Clock },
    RUNNING: { bg: 'bg-blue-100', text: 'text-blue-800', icon: RotateCcw },
    COMPLETED: { bg: 'bg-emerald-100', text: 'text-emerald-800', icon: CheckCircle2 },
    FAILED: { bg: 'bg-rose-100', text: 'text-rose-800', icon: AlertTriangle },
    CANCELLED: { bg: 'bg-amber-100', text: 'text-amber-800', icon: Ban },
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Simulation Execution & Job Queue</h1>
        <p className="text-sm text-slate-500 mt-1">
          Launch multi-replicate stochastic outbreaks, track background execution progress, and inspect outcomes.
        </p>
      </div>

      {/* Launch Box */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-6">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-base">
            <Play className="w-5 h-5 text-blue-600 fill-blue-600" />
            Configure New Simulation Job
          </div>
          <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100">
            <input
              type="checkbox"
              checked={useMock}
              onChange={(e) => setUseMock(e.target.checked)}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            Fast Mock Mode (Offline UI Testing)
          </label>
        </div>

        <form onSubmit={handleLaunch} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Region */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Region Pack</label>
              <select
                value={regionId}
                onChange={(e) => setRegionId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {regions?.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.data_level || 'L0'})
                  </option>
                ))}
              </select>
            </div>

            {/* Disease */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Pathogen Pack</label>
              <select
                value={diseaseId}
                onChange={(e) => setDiseaseId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {diseases?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} (R0 {d.r0 || '3.6'})
                  </option>
                ))}
              </select>
            </div>

            {/* Scenario */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Intervention Scenario</label>
              <select
                value={scenarioId}
                onChange={(e) => setScenarioId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {scenarios?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.n_interventions} actions)
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 pt-2">
            {/* Scale Agents */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Agents: <strong className="text-blue-600">{scaleAgents.toLocaleString()}</strong>
              </label>
              <input
                type="range"
                min={500}
                max={20000}
                step={500}
                value={scaleAgents}
                onChange={(e) => setScaleAgents(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            {/* Replicates */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Replicates: <strong className="text-blue-600">{nReplicates} seeds</strong>
              </label>
              <input
                type="range"
                min={1}
                max={15}
                step={1}
                value={nReplicates}
                onChange={(e) => setNReplicates(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            {/* Horizon Days */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Horizon: <strong className="text-blue-600">{horizonDays} days</strong>
              </label>
              <input
                type="range"
                min={10}
                max={180}
                step={5}
                value={horizonDays}
                onChange={(e) => setHorizonDays(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            {/* Behavior Mode */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Behavior Mode</label>
              <select
                value={behaviorMode}
                onChange={(e) => setBehaviorMode(e.target.value as any)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              >
                <option value="none">none (Unmitigated Baseline)</option>
                <option value="rule">rule (Psychographic Rules)</option>
                <option value="llm">
                  llm ({localBackend?.status === 'available' ? `Local Model: ${localBackend.active_model || 'Ollama'}` : 'Local LLM / AI Decision Agent'})
                </option>
              </select>
              {localBackend?.status === 'available' ? (
                <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>Local Model Detected: <strong>{localBackend.active_model}</strong> (localhost:11434)</span>
                </div>
              ) : (
                <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-slate-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
                  <span>Local LLM: not detected on localhost:11434</span>
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 flex items-center justify-between border-t border-slate-100">
            <span className="text-xs text-slate-500">
              {useMock ? '⚡ Instant synthetic execution fixture' : 'Vectorized NumPy engine execution'}
            </span>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-500 transition-all shadow-md disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-white" />
              {isSubmitting ? 'Enqueuing Job...' : 'Launch Simulation Job'}
            </button>
          </div>
        </form>
      </div>

      {/* Jobs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm">Execution History & Active Queue</h3>
          <span className="text-xs text-slate-500 font-mono">Total: {jobsList?.total || 0} jobs</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold text-[10px]">
                <th className="p-3.5">Job ID</th>
                <th className="p-3.5">Scenario / Region</th>
                <th className="p-3.5">Agents & Mode</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Progress</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(!jobsList?.jobs || jobsList.jobs.length === 0) ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-400">
                    No simulation runs found. Launch one above!
                  </td>
                </tr>
              ) : (
                jobsList.jobs.map((job) => {
                  const badge = statusBadges[job.status];
                  const Icon = badge.icon;
                  return (
                    <tr key={job.job_id} className="hover:bg-slate-50 transition-colors">
                      <td className="p-3.5 font-mono font-medium text-slate-900">
                        {job.job_id}
                        {job.is_mock && (
                          <span className="ml-1.5 text-[9px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 font-bold">
                            MOCK
                          </span>
                        )}
                      </td>
                      <td className="p-3.5">
                        <div className="font-semibold text-slate-800">{job.request.scenario_id}</div>
                        <div className="text-[10px] text-slate-500">{job.request.region_id}</div>
                      </td>
                      <td className="p-3.5">
                        <div className="text-slate-700">{job.request.scale_agents?.toLocaleString()} agents</div>
                        <div className="text-[10px] text-slate-500">
                          {job.request.behavior_mode} · {job.request.n_replicates} seeds
                        </div>
                      </td>
                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                          <Icon className={`w-3 h-3 ${job.status === 'RUNNING' ? 'animate-spin' : ''}`} />
                          {job.status}
                        </span>
                      </td>
                      <td className="p-3.5 w-40">
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full transition-all duration-300 ${
                                job.status === 'FAILED' ? 'bg-rose-500' : 'bg-blue-600'
                              }`}
                              style={{ width: `${Math.round(job.progress * 100)}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono w-8 text-right">
                            {Math.round(job.progress * 100)}%
                          </span>
                        </div>
                      </td>
                      <td className="p-3.5 text-right space-x-2">
                        {job.status === 'COMPLETED' ? (
                          <Link
                            to={`/results/${job.job_id}`}
                            className="inline-flex items-center gap-1 px-3 py-1 rounded bg-blue-50 text-blue-700 font-semibold text-xs hover:bg-blue-100 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" /> Results
                          </Link>
                        ) : job.status === 'RUNNING' || job.status === 'QUEUED' ? (
                          <button
                            onClick={() => cancelMutation.mutate(job.job_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-rose-200 text-rose-600 font-semibold text-xs hover:bg-rose-50"
                          >
                            <Ban className="w-3.5 h-3.5" /> Cancel
                          </button>
                        ) : (
                          <span className="text-slate-400 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

import {
  BackendsResponse,
  CapacityOutput,
  CompareRequest,
  CompareResponse,
  DiseaseSummary,
  EvidenceItem,
  HealthResponse,
  JobCancelResponse,
  JobListResponse,
  JobRecord,
  PackValidationResult,
  ProblemDetail,
  RegionSummary,
  RunCreateRequest,
  RunSummary,
  ScenarioSummary,
  SpatialOutput,
  TimeSeriesData,
  ValidationCardResponse,
  ValidationReportResponse,
  AssumptionItem,
  BehaviorSummary,
} from './types';

const API_BASE = '/api/v1';

export class ApiError extends Error {
  public problem?: ProblemDetail;
  public statusCode: number;

  constructor(message: string, statusCode: number, problem?: ProblemDetail) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.problem = problem;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let problem: ProblemDetail | undefined;
    try {
      const data = await response.json();
      if (data && typeof data === 'object' && 'title' in data && 'status' in data) {
        problem = data as ProblemDetail;
      }
    } catch {
      // not JSON
    }
    const message = problem?.detail || `HTTP ${response.status}: ${response.statusText}`;
    throw new ApiError(message, response.status, problem);
  }

  return response.json();
}

export const api = {
  // System & Health
  getHealth: () => request<HealthResponse>('/health'),
  getBackends: () => request<BackendsResponse>('/backends'),

  // Validation & Provenance
  getValidationCard: () => request<ValidationCardResponse>('/validation/card'),
  getValidationReport: () => request<ValidationReportResponse>('/validation/report'),
  getAssumptions: () => request<AssumptionItem[]>('/validation/assumptions'),
  getEvidence: () => request<EvidenceItem[]>('/validation/evidence'),

  // Packs
  getRegions: () => request<RegionSummary[]>('/packs/regions'),
  getRegion: (id: string) => request<Record<string, any>>(`/packs/regions/${id}`),
  validateRegion: (id: string) => request<PackValidationResult>(`/packs/regions/${id}/validate`, { method: 'POST' }),

  getDiseases: () => request<DiseaseSummary[]>('/packs/diseases'),
  getDisease: (id: string) => request<Record<string, any>>(`/packs/diseases/${id}`),
  validateDisease: (id: string) => request<PackValidationResult>(`/packs/diseases/${id}/validate`, { method: 'POST' }),

  getScenarios: () => request<ScenarioSummary[]>('/packs/scenarios'),
  getScenario: (id: string) => request<Record<string, any>>(`/packs/scenarios/${id}`),
  validateScenario: (id: string) => request<PackValidationResult>(`/packs/scenarios/${id}/validate`, { method: 'POST' }),

  getBehaviors: () => request<BehaviorSummary[]>('/packs/behaviors'),
  getBehavior: (id: string) => request<Record<string, any>>(`/packs/behaviors/${id}`),
  validateBehavior: (id: string) => request<PackValidationResult>(`/packs/behaviors/${id}/validate`, { method: 'POST' }),

  // Runs & Jobs
  launchRun: (req: RunCreateRequest) =>
    request<JobRecord>('/runs', { method: 'POST', body: JSON.stringify(req) }),
  listRuns: (limit = 50, offset = 0) =>
    request<JobListResponse>(`/runs?limit=${limit}&offset=${offset}`),
  getRun: (id: string) => request<JobRecord>(`/runs/${id}`),
  cancelRun: (id: string) => request<JobCancelResponse>(`/runs/${id}/cancel`, { method: 'POST' }),

  getRunSummary: (id: string) => request<RunSummary>(`/runs/${id}/summary`),
  getRunTimeseries: (id: string) => request<TimeSeriesData>(`/runs/${id}/timeseries`),
  getRunSpatial: (id: string) => request<SpatialOutput>(`/runs/${id}/spatial`),
  getRunCapacity: (id: string) => request<CapacityOutput>(`/runs/${id}/capacity`),

  // Compare & What-If
  compareScenarios: (req: CompareRequest) =>
    request<CompareResponse>('/compare', { method: 'POST', body: JSON.stringify(req) }),
  whatIfAnalysis: (req: CompareRequest) =>
    request<CompareResponse>('/what-if', { method: 'POST', body: JSON.stringify(req) }),
};

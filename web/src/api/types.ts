/**
 * Typed domain interfaces derived from OpenAPI 3.1.0 specification.
 */

export type JobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface BackendItem {
  name: string;
  status: string;
  configured: boolean;
  active_model?: string | null;
  details: Record<string, any>;
}

export interface BackendsResponse {
  backends: BackendItem[];
}

export interface RegionSummary {
  id: string;
  name: string;
  country_iso?: string | null;
  data_year?: number | null;
  data_level?: string | null;
  num_areas?: number | null;
  total_population?: number | null;
  areas_file_exists: boolean;
  contacts_file_exists: boolean;
  commute_file_exists: boolean;
  observed_cases_exists: boolean;
  provenance_status: 'REAL' | 'SYNTHETIC';
  notes?: string | null;
}

export interface DiseaseSummary {
  id: string;
  name: string;
  r0?: number | null;
  incubation_days?: number | null;
  infectious_days?: number | null;
  case_fatality_ratio?: number | null;
  states_count: number;
  has_vulnerability_factors: boolean;
  description?: string | null;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  horizon_days: number;
  behavior_mode: string;
  n_interventions: number;
  description?: string | null;
}

export interface BehaviorSummary {
  id: string;
  name: string;
  context?: string | null;
  rumor_spread_rate?: number | null;
  n_rumor_topics: number;
  n_questions: number;
}

export interface PackValidationResult {
  pack_type: string;
  pack_id: string;
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  details: Record<string, any>;
}

export interface RunCreateRequest {
  region_id?: string;
  disease_id?: string;
  scenario_id?: string;
  scale_agents?: number;
  behavior_mode?: 'none' | 'rule' | 'llm';
  n_replicates?: number;
  random_seed?: number;
  horizon_days?: number | null;
  pause_at_day?: number | null;
  use_mock?: boolean;
}

export interface JobRecord {
  job_id: string;
  status: JobStatus;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  progress: number;
  current_day: number;
  total_days: number;
  request: RunCreateRequest;
  error?: string | null;
  results_summary?: Record<string, any> | null;
  is_mock: boolean;
}

export interface JobListResponse {
  jobs: JobRecord[];
  total: number;
}

export interface JobCancelResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface MetricBounds {
  mean: number;
  ci_lower: number;
  ci_upper: number;
  std?: number | null;
}

export interface MetricsSummary {
  attack_rate: MetricBounds;
  peak_day: MetricBounds;
  total_deaths: MetricBounds;
  peak_hospital_demand: MetricBounds;
  peak_icu_demand: MetricBounds;
  overflow_deaths?: MetricBounds | null;
}

export interface RunSummary {
  job_id: string;
  region_id: string;
  disease_id: string;
  scenario_id: string;
  behavior_mode: string;
  scale_agents: number;
  n_replicates: number;
  metrics: MetricsSummary;
  validation_status: string;
  validation_card_url: string;
  is_mock: boolean;
  banner?: string | null;
}

export interface TimeSeriesData {
  job_id: string;
  horizon_days: number;
  days: number[];
  state_names: string[];
  daily_states: Record<string, number[]>;
  daily_hospital_demand: number[];
  daily_icu_demand: number[];
  daily_deaths: number[];
  daily_mean_compliance?: number[] | null;
  daily_rumor_beliefs?: Record<string, number[]> | null;
  is_mock: boolean;
}

export interface AreaSpatialPoint {
  area_id: string;
  name: string;
  population: number;
  density: number;
  iso_x: number;
  iso_y: number;
  total_infections: number;
  attack_rate: number;
  daily_incident_infections: number[];
  peak_day: number;
}

export interface SpatialOutput {
  job_id: string;
  region_id: string;
  n_areas: number;
  areas: AreaSpatialPoint[];
  layers: Array<{ id: string; name: string; color: string; altitude: number }>;
  is_mock: boolean;
}

export interface CapacityOutput {
  job_id: string;
  hospital_capacity_beds: number;
  icu_capacity_beds: number;
  daily_hospital_demand: number[];
  daily_icu_demand: number[];
  overflow_days_hospital: number;
  overflow_days_icu: number;
  overflow_deaths: number;
  daily_unmet_demand: Record<string, number[]>;
  is_mock: boolean;
}

export interface CompareRequest {
  region_id?: string;
  disease_id?: string;
  scenario_a?: string;
  scenario_b?: string;
  scale_agents?: number;
  n_replicates?: number;
  random_seed?: number;
  behavior_mode?: string;
}

export interface CompareResponse {
  scenario_a: string;
  scenario_b: string;
  n_replicates: number;
  means_a: Record<string, number>;
  delta_means: Record<string, number>;
  delta_ci_95_lower: Record<string, number>;
  delta_ci_95_upper: Record<string, number>;
  comparison: Record<string, number>;
  validation_status: string;
}

export interface AssumptionItem {
  parameter: string;
  value: any;
  source: string;
  status: string;
  notes?: string | null;
}

export interface EvidenceItem {
  id: string;
  url: string;
  retrieved_at: string;
  sha256: string;
  byte_count: number;
  http_status?: number | null;
  content_type: string;
  license: string;
  file_path: string;
  record_status: string;
  notes?: string | null;
  record_type: string;
  parent_ids?: string | null;
  transform_script?: string | null;
  transform_script_sha256?: string | null;
}

export interface ValidationCardResponse {
  status: string;
  region?: string;
  calibration_window?: string;
  calibrated_parameters?: Record<string, any>;
  targets_passed?: string;
  targets?: Record<string, any>;
  ledger_authenticated?: boolean;
  generated_at?: string;
  [key: string]: any;
}

export interface ValidationReportResponse {
  status: string;
  report_markdown: string;
  assumptions_count: number;
}

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string | null;
  invalid_params?: Array<{ name: string; reason: string; type: string }> | null;
}

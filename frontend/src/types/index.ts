export type HealthResponse = {
  status: string
  service: string
  phase: number | string
  timestamp: string
}

export type SystemStatus = {
  name: string
  subtitle: string
  system_status: string
  active_incidents: number
  critical_incidents: number
  alerts: number
  services_healthy: number
  services_warning: number
  services_critical: number
  services_total: number
  mttr_seconds: number
  auto_resolved: number
}

export type ServiceStatus = 'HEALTHY' | 'WARNING' | 'CRITICAL'

export type Service = {
  id: string
  name: string
  status: ServiceStatus
  criticality: string
  dependencies: string[]
  metrics: Record<string, number>
}

export type Alert = {
  id: string
  timestamp: string
  service: string
  type: string
  severity: string
  message: string
  metric: string
  value: number
  threshold: number
}

export type Metrics = {
  database_cpu: number
  database_connections: number
  payment_latency_ms: number
  checkout_error_rate: number
  api_5xx_rate: number
  failed_transactions: number
  traffic_rps: number
  network_latency_ms: number
}

export type MetricHistoryPoint = {
  timestamp: string
  database_cpu: number
  database_connections: number
  payment_latency_ms: number
  checkout_error_rate: number
  api_5xx_rate: number
}

export type Simulation = {
  active: boolean
  scenario: string | null
  scenario_label: string | null
  progress: number
  started_at: string | null
  phase: string
}

export type ScoreBreakdown = {
  temporal_evidence: number
  dependency_evidence: number
  log_evidence: number
  blast_radius_evidence: number
  historical_similarity: number
}

export type Hypothesis = {
  id: string
  component: string
  cause: string
  score: number
  confidence: number
  score_breakdown: ScoreBreakdown
  evidence: string[]
  counter_evidence: string[]
  affected_dependency_paths: string[]
}

export type RCA = {
  status: string
  method: string
  top_hypothesis: Hypothesis
  hypotheses: Hypothesis[]
  explanation: string
}

export type Correlation = {
  correlated: boolean
  alert_count: number
  affected_services: string[]
  timestamp_span_seconds: number
  signature_matches: number
  topology_links: string[]
  correlation_strength: number
  reasons: string[]
}


export type CounterfactualSymptom = {
  name: string
  effect: string
  explained: boolean
}

export type Counterfactual = {
  status: string
  hypothesis: string
  component: string
  question: string
  symptoms: CounterfactualSymptom[]
  explained_symptoms: number
  total_symptoms: number
  explanation_ratio: number
  causal_support: 'HIGH' | 'MEDIUM' | 'LOW'
  reasoning: string
  method: string
}

export type BusinessImpact = {
  severity: string
  impact_score: number
  affected_services: number
  affected_service_names: string[]
  users_affected: number
  failed_transactions: number
  estimated_revenue_risk_inr_per_hour: number
  sla_violation: boolean
  business_criticality: string
  technical_severity_score: number
  source: string
  disclaimer: string
}

export type RemediationCandidate = {
  id: string
  action: string
  risk: string
  cost: string
  disruption: string
  effectiveness: string
  directness: number
  selection_score: number
  requires_approval: boolean
  autonomy_level: number
}

export type RemediationContract = {
  action: string
  success_conditions: Array<{ metric: string; operator: string; threshold: number; label: string }>
  failure_conditions: string[]
  observation_period_seconds: number
  rollback_action: string
  status: string
}

export type Remediation = {
  engine: string
  status: string
  root_cause: string
  root_cause_confidence: number
  recommended_action: RemediationCandidate
  candidates: RemediationCandidate[]
  why_selected: string[]
  autonomy: {
    level: number
    state: string
    requires_approval: boolean
    auto_execute?: boolean
    action_risk?: string
    policy_reason?: string
  }
  contract: RemediationContract
}


export type ReasoningDebateTurn = {
  role: string
  statement: string
}

export type ReasoningDebate = {
  status: string
  mode: string
  disclaimer: string
  turns: ReasoningDebateTurn[]
  decision: string
}

export type Incident = {
  id: string
  created_at: string
  status: string
  severity: string
  scenario: string | null
  title: string
  related_alerts: string[]
  alert_count: number
  affected_services: string[]
  correlation: Correlation
  root_cause: string | null
  confidence: number
  rca: RCA | null
  counterfactual: Counterfactual | null
  business_impact: BusinessImpact | null
  remediation: Remediation | null
  remediation_state: string
  verification: Verification | null
  force_remediation_failure: boolean
  resolved_at: string | null
  alert_types: string[]
  fingerprint: string[]
  historical_match: HistoricalMatch | null
  reasoning_debate: ReasoningDebate | null
  incident_risk?: { level: string; impact_score: number; reason: string }
}


export type AdaptiveMonitoring = {
  pattern: 'LEARNING' | 'NORMAL' | 'SUSPICIOUS' | 'ANOMALOUS'
  anomaly_score: number
  raw_anomaly_score: number
  suspicious_threshold: number
  anomaly_threshold: number
  predicted_incident: string
  prediction_confidence: number
  probabilities: Record<string, number>
  learning_enabled: boolean
  baseline_status: string
  observations_learned: number
  confirmed_incidents_learned: number
  drift_events: number
  drifted_features: string[]
  model: {
    anomaly_detector: string
    incident_classifier: string
    drift_detector: string
  }
}


export type NotificationEvent = {
  key: string
  timestamp: string
  kind: string
  incident_id: string | null
  subject: string
  recipient: string | null
  status: string
  detail: string
}

export type NotificationConfig = {
  enabled: boolean
  configured: boolean
  host: string | null
  port: number
  username: string | null
  admin_email: string | null
  from_email: string | null
  use_tls: boolean
}

export type Snapshot = {
  system: SystemStatus
  simulation: Simulation
  metrics: Metrics
  adaptive_monitoring: AdaptiveMonitoring
  services: Service[]
  alerts: Alert[]
  incident: Incident | null
  history: MetricHistoryPoint[]
  audit: AuditEvent[]
  historical_incidents: HistoricalIncident[]
  persistent_audit: AuditEvent[]
  notifications: NotificationEvent[]
  notification_config: NotificationConfig
}


export type VerificationCheck = {
  metric: string
  label: string
  value: number
  threshold: number
  operator: string
  passed: boolean
}

export type Verification = {
  status: 'PASSED' | 'FAILED'
  passed: boolean
  passed_checks: number
  total_checks: number
  checks: VerificationCheck[]
}

export type AuditEvent = {
  timestamp: string
  incident_id: string | null
  event_type: string
  message: string
  details: Record<string, unknown>
}


export type HistoricalMatch = {
  incident_id: string
  similarity: number
  previous_root_cause: string | null
  previous_successful_remediation: string | null
  recovery: string
  matched_alerts: string[]
  method: string
}

export type HistoricalIncident = {
  id: string
  sequence: number
  created_at: string
  resolved_at: string | null
  status: string
  scenario: string | null
  severity: string
  title: string
  root_cause: string | null
  confidence: number
  remediation_action: string | null
  recovery_successful: boolean
  fingerprint: string[]
  alert_types: string[]
  affected_services: string[]
}

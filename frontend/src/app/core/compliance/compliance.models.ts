/**
 * Contract for `backend/src/modules/compliance/` (Phase 8). Field names mirror the
 * backend's snake_case Pydantic DTOs -- keep in sync if those change.
 */

/** AML alert status state machine. */
export type AmlAlertStatus = 'OPEN' | 'UNDER_REVIEW' | 'DISMISSED' | 'ESCALATED';

/** Closed set of alert types the backend generates. */
export type AmlAlertType =
  | 'HIGH_VALUE_TRANSACTION'
  | 'RAPID_MOVEMENT'
  | 'SANCTIONED_JURISDICTION'
  | 'PEP_MATCH'
  | 'SUSPICIOUS_PATTERN';

/** `GET /compliance/aml-alerts` item. */
export interface AmlAlert {
  id: number;
  transaction_ref: string;
  investor_id: number;
  investor_name: string;
  alert_type: AmlAlertType;
  risk_score: number;
  status: AmlAlertStatus;
  assigned_officer_id: number | null;
  assigned_officer_name: string | null;
  created_at: string;
  updated_at: string;
  details: Record<string, unknown> | null;
}

/** `GET /compliance/aml-alerts` response. */
export interface AmlAlertListResponse {
  total: number;
  items: AmlAlert[];
}

/** `PATCH /compliance/aml-alerts/:id/assign` request body. */
export interface AssignAlertRequest {
  officer_id: number;
}

/** `PATCH /compliance/aml-alerts/:id/resolve` request body. */
export interface ResolveAlertRequest {
  status: 'DISMISSED' | 'ESCALATED';
  notes: string;
}

/** Compliance report types. */
export type ComplianceReportType = 'QUARTERLY_IFSCA' | 'ANNUAL_FINANCIALS';

/** Report generation status. */
export type ReportStatus = 'GENERATING' | 'COMPLETED' | 'FAILED';

/** `GET /compliance/reports` item / `POST /compliance/reports/generate` response. */
export interface ComplianceReport {
  id: number;
  report_type: ComplianceReportType;
  period_start: string;
  period_end: string;
  status: ReportStatus;
  generated_by_user_id: number;
  generated_by_name: string;
  created_at: string;
  completed_at: string | null;
  object_key: string | null;
}

/** `POST /compliance/reports/generate` request body. */
export interface GenerateReportRequest {
  report_type: ComplianceReportType;
  period_start: string;
  period_end: string;
}

/** `GET /compliance/reports/:id/download` response. */
export interface ReportDownloadResponse {
  url: string;
}

/** Audit log entity types. */
export type AuditEntityType =
  | 'USER'
  | 'INVESTOR_PROFILE'
  | 'KYC_SUBMISSION'
  | 'ISSUANCE_PROPOSAL'
  | 'SUBSCRIPTION'
  | 'REDEMPTION'
  | 'WALLET_MAPPING'
  | 'FUNDING_INSTRUCTION'
  | 'AML_ALERT';

/** `GET /compliance/audit-log` item. */
export interface AuditLogEntry {
  id: number;
  timestamp: string;
  actor_user_id: number;
  actor_email: string;
  actor_name: string | null;
  action: string;
  entity_type: AuditEntityType;
  entity_id: number;
  ip_address: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
}

/** `GET /compliance/audit-log` response. */
export interface AuditLogListResponse {
  total: number;
  items: AuditLogEntry[];
}

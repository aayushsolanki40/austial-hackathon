import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api/api.service';
import type {
  AmlAlert,
  AmlAlertListResponse,
  AssignAlertRequest,
  ResolveAlertRequest,
  ComplianceReport,
  GenerateReportRequest,
  ReportDownloadResponse,
  AuditLogEntry,
  AuditLogListResponse,
} from './compliance.models';

/**
 * API client for `backend/src/modules/compliance/` (Phase 8). All endpoints are
 * role-gated to `COMPLIANCE_OFFICER` or `ADMIN` on the backend side (see
 * `compliance_controller.py`), and the frontend routes calling this service already
 * enforce matching `roleGuard` constraints.
 */
@Injectable({ providedIn: 'root' })
export class ComplianceService {
  private readonly api = inject(ApiService);

  // -- AML Alerts ----------------------------------------------------------------------------

  /** `GET /compliance/aml-alerts?status=&assigned_to_me=&alert_type=` -- filtered queue. */
  getAmlAlerts(filters?: {
    status?: string;
    assigned_to_me?: boolean;
    alert_type?: string;
  }): Observable<AmlAlertListResponse> {
    return this.api.get<AmlAlertListResponse>('/compliance/aml-alerts', filters);
  }

  /** `PATCH /compliance/aml-alerts/:id/assign` -- assign to a specific officer. */
  assignAlert(alertId: number, body: AssignAlertRequest): Observable<AmlAlert> {
    return this.api.patch<AmlAlert>(`/compliance/aml-alerts/${alertId}/assign`, body);
  }

  /** `PATCH /compliance/aml-alerts/:id/resolve` -- dismiss or escalate. */
  resolveAlert(alertId: number, body: ResolveAlertRequest): Observable<AmlAlert> {
    return this.api.patch<AmlAlert>(`/compliance/aml-alerts/${alertId}/resolve`, body);
  }

  // -- Reports -------------------------------------------------------------------------------

  /** `GET /compliance/reports` -- list all generated reports. */
  getReports(): Observable<ComplianceReport[]> {
    return this.api.get<ComplianceReport[]>('/compliance/reports');
  }

  /** `POST /compliance/reports/generate` -- trigger a new report generation job. */
  generateReport(body: GenerateReportRequest): Observable<ComplianceReport> {
    return this.api.post<ComplianceReport>('/compliance/reports/generate', body);
  }

  /** `GET /compliance/reports/:id/download` -- get a presigned S3 URL. */
  getReportDownloadUrl(reportId: number): Observable<ReportDownloadResponse> {
    return this.api.get<ReportDownloadResponse>(`/compliance/reports/${reportId}/download`);
  }

  // -- Audit Log -----------------------------------------------------------------------------

  /** `GET /compliance/audit-log?entity_type=&from=&to=&actor=` -- filtered immutable log. */
  getAuditLog(filters?: {
    entity_type?: string;
    from?: string;
    to?: string;
    actor?: string;
  }): Observable<AuditLogListResponse> {
    return this.api.get<AuditLogListResponse>('/compliance/audit-log', filters);
  }
}

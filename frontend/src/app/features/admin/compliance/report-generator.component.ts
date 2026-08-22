import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';

import { ComplianceService } from '../../../core/compliance/compliance.service';
import type { ComplianceReport, ComplianceReportType, ReportStatus } from '../../../core/compliance/compliance.models';
import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { AdminStateComponent } from '../shared/admin-state.component';
import { StatusBadgeComponent } from '../shared/status-badge.component';
import { FormFieldComponent } from '../../../shared/components/form-field/form-field.component';
import { SelectComponent, type SelectOption } from '../../../shared/components/select/select.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 8 compliance report generator. Allows compliance officers to generate IFSCA
 * quarterly and annual financial reports, then view and download the generated reports.
 */
@Component({
  selector: 'app-report-generator',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    AdminStateComponent,
    StatusBadgeComponent,
    FormFieldComponent,
    SelectComponent,
    TPipe,
    FormsModule,
  ],
  templateUrl: './report-generator.component.html',
  styleUrl: './report-generator.component.scss',
})
export default class ReportGeneratorComponent implements OnInit {
  private readonly complianceService = inject(ComplianceService);
  private readonly i18n = inject(I18nService);

  readonly state = signal<LoadState>('loading');
  readonly reports = signal<ComplianceReport[]>([]);
  readonly generating = signal(false);
  readonly downloadingId = signal<number | null>(null);

  readonly reportType = signal<ComplianceReportType>('QUARTERLY_IFSCA');
  readonly periodStart = signal<string>('');
  readonly periodEnd = signal<string>('');

  readonly displayedColumns = [
    'report_type',
    'period',
    'status',
    'generated_by_name',
    'created_at',
    'actions',
  ];

  readonly reportTypeOptions: SelectOption[] = [
    { value: 'QUARTERLY_IFSCA', label: 'Quarterly IFSCA Report' },
    { value: 'ANNUAL_FINANCIALS', label: 'Annual Financials' },
  ];

  ngOnInit(): void {
    this.loadReports();
  }

  loadReports(): void {
    this.state.set('loading');
    this.complianceService.getReports().subscribe({
      next: (reports) => {
        this.reports.set(reports);
        this.state.set('loaded');
      },
      error: () => this.state.set('error'),
    });
  }

  canGenerate(): boolean {
    return !!this.periodStart() && !!this.periodEnd();
  }

  generateReport(): void {
    if (!this.canGenerate() || this.generating()) return;

    const start = this.periodStart();
    const end = this.periodEnd();

    this.generating.set(true);
    this.complianceService
      .generateReport({
        report_type: this.reportType(),
        period_start: start,
        period_end: end,
      })
      .subscribe({
        next: (newReport) => {
          this.generating.set(false);
          this.reports.update((reports) => [newReport, ...reports]);
          this.periodStart.set('');
          this.periodEnd.set('');
        },
        error: () => this.generating.set(false),
      });
  }

  statusColor(status: ReportStatus): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'COMPLETED':
        return 'success';
      case 'GENERATING':
        return 'warning';
      case 'FAILED':
        return 'error';
      default:
        return 'default';
    }
  }

  downloadReport(report: ComplianceReport): void {
    if (report.status !== 'COMPLETED' || this.downloadingId()) return;

    this.downloadingId.set(report.id);
    this.complianceService.getReportDownloadUrl(report.id).subscribe({
      next: (response) => {
        window.open(response.url, '_blank');
        this.downloadingId.set(null);
      },
      error: () => this.downloadingId.set(null),
    });
  }

  formatPeriod(report: ComplianceReport): string {
    const start = new Date(report.period_start).toLocaleDateString();
    const end = new Date(report.period_end).toLocaleDateString();
    return `${start} – ${end}`;
  }

  getReportTypeLabel(reportType: ComplianceReportType): string {
    const option = this.reportTypeOptions.find((opt) => opt.value === reportType);
    return option ? option.label : reportType;
  }
}

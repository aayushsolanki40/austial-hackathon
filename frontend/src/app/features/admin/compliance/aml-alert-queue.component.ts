import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';

import { AuthService } from '../../../core/auth/auth.service';
import { ComplianceService } from '../../../core/compliance/compliance.service';
import type { AmlAlert, AmlAlertStatus, AmlAlertType } from '../../../core/compliance/compliance.models';
import { TPipe } from '../../../core/i18n/t.pipe';
import { AdminStateComponent } from '../shared/admin-state.component';
import { StatusBadgeComponent } from '../shared/status-badge.component';
import { ResolveAlertDialogComponent } from './resolve-alert-dialog.component';

type LoadState = 'loading' | 'error' | 'loaded';

const PAGE_SIZE = 50;

/**
 * Phase 8 AML alert queue with resolution workflow. Gated by
 * `roleGuard(['COMPLIANCE_OFFICER', 'ADMIN'])` in `admin.routes.ts`.
 *
 * Displays alerts with color-coded risk scores (red >80, yellow 50-80, green <50),
 * filterable by status/assignment/type, with assign-to-me and resolve actions per row.
 * Resolution opens a dialog (dismiss or escalate + notes).
 */
@Component({
  selector: 'app-aml-alert-queue',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatDialogModule,
    AdminStateComponent,
    StatusBadgeComponent,
    TPipe,
    FormsModule,
  ],
  templateUrl: './aml-alert-queue.component.html',
  styleUrl: './aml-alert-queue.component.scss',
})
export default class AmlAlertQueueComponent implements OnInit {
  private readonly complianceService = inject(ComplianceService);
  private readonly authService = inject(AuthService);
  private readonly dialog = inject(MatDialog);

  readonly state = signal<LoadState>('loading');
  readonly alerts = signal<AmlAlert[]>([]);
  readonly actioningId = signal<number | null>(null);

  readonly statusFilter = signal<AmlAlertStatus | ''>('');
  readonly assignedToMeFilter = signal(false);
  readonly alertTypeFilter = signal<AmlAlertType | ''>('');

  readonly displayedColumns = [
    'transaction_ref',
    'investor_name',
    'alert_type',
    'risk_score',
    'status',
    'assigned_officer_name',
    'created_at',
    'actions',
  ];

  readonly statusOptions: AmlAlertStatus[] = ['OPEN', 'UNDER_REVIEW', 'DISMISSED', 'ESCALATED'];
  readonly alertTypeOptions: AmlAlertType[] = [
    'HIGH_VALUE_TRANSACTION',
    'RAPID_MOVEMENT',
    'SANCTIONED_JURISDICTION',
    'PEP_MATCH',
    'SUSPICIOUS_PATTERN',
  ];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    const filters: { status?: string; assigned_to_me?: boolean; alert_type?: string } = {};
    if (this.statusFilter()) {
      filters.status = this.statusFilter();
    }
    if (this.assignedToMeFilter()) {
      filters.assigned_to_me = true;
    }
    if (this.alertTypeFilter()) {
      filters.alert_type = this.alertTypeFilter();
    }

    this.complianceService.getAmlAlerts(filters).subscribe({
      next: (response) => {
        this.alerts.set(response.items);
        this.state.set('loaded');
      },
      error: () => this.state.set('error'),
    });
  }

  applyFilters(): void {
    this.load();
  }

  riskScoreClass(score: number): string {
    if (score > 80) return 'risk-score--high';
    if (score >= 50) return 'risk-score--medium';
    return 'risk-score--low';
  }

  statusColor(status: AmlAlertStatus): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'DISMISSED':
        return 'success';
      case 'ESCALATED':
        return 'error';
      case 'UNDER_REVIEW':
        return 'warning';
      case 'OPEN':
        return 'info';
      default:
        return 'default';
    }
  }

  assignToMe(alert: AmlAlert): void {
    const claims = this.authService.claims();
    if (!claims) return;

    const officerId = parseInt(claims.sub, 10);
    if (isNaN(officerId)) return;

    this.actioningId.set(alert.id);
    this.complianceService.assignAlert(alert.id, { officer_id: officerId }).subscribe({
      next: (updated) => {
        this.actioningId.set(null);
        this.alerts.update((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      },
      error: () => this.actioningId.set(null),
    });
  }

  openResolveDialog(alert: AmlAlert): void {
    const dialogRef = this.dialog.open(ResolveAlertDialogComponent, {
      width: '500px',
      data: { alert },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (!result) return;

      this.actioningId.set(alert.id);
      this.complianceService.resolveAlert(alert.id, result).subscribe({
        next: (updated) => {
          this.actioningId.set(null);
          this.alerts.update((items) => items.map((item) => (item.id === updated.id ? updated : item)));
        },
        error: () => this.actioningId.set(null),
      });
    });
  }

  isActioning(alertId: number): boolean {
    return this.actioningId() === alertId;
  }
}

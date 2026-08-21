import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatNativeDateModule } from '@angular/material/core';

import { ComplianceService } from '../../../core/compliance/compliance.service';
import type { AuditEntityType, AuditLogEntry } from '../../../core/compliance/compliance.models';
import { TPipe } from '../../../core/i18n/t.pipe';
import { AdminStateComponent } from '../shared/admin-state.component';
import { AuditLogDetailsDialogComponent } from './audit-log-details-dialog.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 8 immutable audit log viewer. Displays all state-change actions across the
 * platform with filters for date range, entity type, and actor. Shows before/after state
 * diffs in a modal dialog when "View details" is clicked.
 */
@Component({
  selector: 'app-audit-log-viewer',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatDialogModule,
    AdminStateComponent,
    TPipe,
    FormsModule,
  ],
  templateUrl: './audit-log-viewer.component.html',
  styleUrl: './audit-log-viewer.component.scss',
})
export default class AuditLogViewerComponent implements OnInit {
  private readonly complianceService = inject(ComplianceService);
  private readonly dialog = inject(MatDialog);

  readonly state = signal<LoadState>('loading');
  readonly entries = signal<AuditLogEntry[]>([]);

  readonly entityTypeFilter = signal<AuditEntityType | ''>('');
  readonly dateFromFilter = signal<Date | null>(null);
  readonly dateToFilter = signal<Date | null>(null);
  readonly actorFilter = signal('');

  readonly displayedColumns = [
    'timestamp',
    'actor_email',
    'action',
    'entity_type',
    'entity_id',
    'ip_address',
    'actions',
  ];

  readonly entityTypeOptions: AuditEntityType[] = [
    'USER',
    'INVESTOR_PROFILE',
    'KYC_SUBMISSION',
    'ISSUANCE_PROPOSAL',
    'SUBSCRIPTION',
    'REDEMPTION',
    'WALLET_MAPPING',
    'FUNDING_INSTRUCTION',
    'AML_ALERT',
  ];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    const filters: { entity_type?: string; from?: string; to?: string; actor?: string } = {};
    if (this.entityTypeFilter()) {
      filters.entity_type = this.entityTypeFilter();
    }
    if (this.dateFromFilter()) {
      filters.from = this.formatDate(this.dateFromFilter()!);
    }
    if (this.dateToFilter()) {
      filters.to = this.formatDate(this.dateToFilter()!);
    }
    if (this.actorFilter().trim()) {
      filters.actor = this.actorFilter().trim();
    }

    this.complianceService.getAuditLog(filters).subscribe({
      next: (response) => {
        this.entries.set(response.items);
        this.state.set('loaded');
      },
      error: () => this.state.set('error'),
    });
  }

  applyFilters(): void {
    this.load();
  }

  clearFilters(): void {
    this.entityTypeFilter.set('');
    this.dateFromFilter.set(null);
    this.dateToFilter.set(null);
    this.actorFilter.set('');
    this.load();
  }

  openDetailsDialog(entry: AuditLogEntry): void {
    this.dialog.open(AuditLogDetailsDialogComponent, {
      width: '800px',
      data: { entry },
    });
  }

  private formatDate(date: Date): string {
    return date.toISOString();
  }
}

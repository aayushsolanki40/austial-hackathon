import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';

import type { AuditLogEntry } from '../../../core/compliance/compliance.models';
import { TPipe } from '../../../core/i18n/t.pipe';

interface DialogData {
  entry: AuditLogEntry;
}

/**
 * Dialog showing before/after state diffs for an audit log entry. Uses simple
 * side-by-side JSON display for clarity (not a dedicated diff library).
 */
@Component({
  selector: 'app-audit-log-details-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, TPipe],
  template: `
    <h2 mat-dialog-title>{{ 'compliance.audit_log_details.title' | t }}</h2>
    <mat-dialog-content>
      <div class="entry-header">
        <div class="header-item">
          <span class="label">{{ 'compliance.audit_log_details.action_label' | t }}:</span>
          <span class="value">{{ data.entry.action }}</span>
        </div>
        <div class="header-item">
          <span class="label">{{ 'compliance.audit_log_details.entity_label' | t }}:</span>
          <span class="value">{{ data.entry.entity_type }} #{{ data.entry.entity_id }}</span>
        </div>
        <div class="header-item">
          <span class="label">{{ 'compliance.audit_log_details.actor_label' | t }}:</span>
          <span class="value">{{ data.entry.actor_email }}</span>
        </div>
        <div class="header-item">
          <span class="label">{{ 'compliance.audit_log_details.timestamp_label' | t }}:</span>
          <span class="value">{{ data.entry.timestamp | date: 'medium' }}</span>
        </div>
      </div>

      <div class="state-diff">
        <div class="state-panel">
          <h3>{{ 'compliance.audit_log_details.before_state_label' | t }}</h3>
          @if (data.entry.before_state) {
            <pre class="state-json">{{ data.entry.before_state | json }}</pre>
          } @else {
            <p class="null-state">{{ 'compliance.audit_log_details.no_before_state' | t }}</p>
          }
        </div>

        <div class="state-panel">
          <h3>{{ 'compliance.audit_log_details.after_state_label' | t }}</h3>
          @if (data.entry.after_state) {
            <pre class="state-json">{{ data.entry.after_state | json }}</pre>
          } @else {
            <p class="null-state">{{ 'compliance.audit_log_details.no_after_state' | t }}</p>
          }
        </div>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="close()">{{ 'compliance.audit_log_details.close_action' | t }}</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      mat-dialog-content {
        max-height: 70vh;
        overflow: auto;
      }

      .entry-header {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background-color: #f5f5f5;
        border-radius: 4px;

        .header-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;

          .label {
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            color: rgba(0, 0, 0, 0.6);
          }

          .value {
            font-size: 0.875rem;
          }
        }
      }

      .state-diff {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;

        .state-panel {
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          overflow: hidden;

          h3 {
            margin: 0;
            padding: 0.75rem 1rem;
            background-color: #fafafa;
            font-size: 0.875rem;
            font-weight: 500;
            border-bottom: 1px solid #e0e0e0;
          }

          .state-json {
            margin: 0;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            background-color: #ffffff;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .null-state {
            margin: 0;
            padding: 1rem;
            color: rgba(0, 0, 0, 0.38);
            font-style: italic;
          }
        }
      }
    `,
  ],
})
export class AuditLogDetailsDialogComponent {
  constructor(
    private dialogRef: MatDialogRef<AuditLogDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
  ) {}

  close(): void {
    this.dialogRef.close();
  }
}

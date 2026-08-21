import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';

import type { AmlAlert } from '../../../core/compliance/compliance.models';
import { TPipe } from '../../../core/i18n/t.pipe';

interface DialogData {
  alert: AmlAlert;
}

interface DialogResult {
  status: 'DISMISSED' | 'ESCALATED';
  notes: string;
}

/**
 * Dialog for resolving an AML alert (dismiss or escalate + resolution notes).
 */
@Component({
  selector: 'app-resolve-alert-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
    TPipe,
    FormsModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ 'compliance.resolve_dialog.title' | t }}</h2>
    <mat-dialog-content>
      <p class="alert-ref">
        {{ 'compliance.resolve_dialog.alert_ref_label' | t }}: <strong>{{ data.alert.transaction_ref }}</strong>
      </p>

      <mat-radio-group [(ngModel)]="selectedStatus">
        <mat-radio-button value="DISMISSED">
          {{ 'compliance.resolve_dialog.dismiss_option' | t }}
        </mat-radio-button>
        <mat-radio-button value="ESCALATED">
          {{ 'compliance.resolve_dialog.escalate_option' | t }}
        </mat-radio-button>
      </mat-radio-group>

      <mat-form-field appearance="outline" class="notes-field">
        <mat-label>{{ 'compliance.resolve_dialog.notes_label' | t }}</mat-label>
        <textarea matInput rows="4" [(ngModel)]="notes"></textarea>
      </mat-form-field>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="cancel()">{{ 'compliance.resolve_dialog.cancel_action' | t }}</button>
      <button mat-flat-button color="primary" (click)="confirm()" [disabled]="!canConfirm()">
        {{ 'compliance.resolve_dialog.confirm_action' | t }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .alert-ref {
        margin-bottom: 1rem;
        color: rgba(0, 0, 0, 0.6);
      }

      mat-radio-group {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-bottom: 1rem;
      }

      .notes-field {
        width: 100%;
      }

      mat-dialog-actions {
        padding: 1rem 0 0;
      }
    `,
  ],
})
export class ResolveAlertDialogComponent {
  selectedStatus: 'DISMISSED' | 'ESCALATED' | null = null;
  notes = '';

  constructor(
    private dialogRef: MatDialogRef<ResolveAlertDialogComponent, DialogResult | undefined>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
  ) {}

  canConfirm(): boolean {
    return !!this.selectedStatus && this.notes.trim().length > 0;
  }

  confirm(): void {
    if (!this.canConfirm() || !this.selectedStatus) return;
    this.dialogRef.close({ status: this.selectedStatus, notes: this.notes.trim() });
  }

  cancel(): void {
    this.dialogRef.close(undefined);
  }
}

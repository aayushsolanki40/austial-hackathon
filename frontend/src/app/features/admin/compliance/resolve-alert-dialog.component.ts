import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogModule, DialogRef } from '@angular/cdk/dialog';

import type { AmlAlert } from '../../../core/compliance/compliance.models';
import { TPipe } from '../../../core/i18n/t.pipe';
import { FormFieldComponent } from '../../../shared/components/form-field/form-field.component';

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
    DialogModule,
    TPipe,
    FormsModule,
    FormFieldComponent,
  ],
  template: `
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full">
      <div class="px-6 py-4 border-b border-slate-200">
        <h2 class="text-xl font-bold text-slate-900">{{ 'compliance.resolve_dialog.title' | t }}</h2>
      </div>
      <div class="px-6 py-4">
        <p class="alert-ref">
          {{ 'compliance.resolve_dialog.alert_ref_label' | t }}: <strong>{{ data.alert.transaction_ref }}</strong>
        </p>

        <div class="radio-group">
          <label class="radio-option">
            <input type="radio" name="status" value="DISMISSED" [(ngModel)]="selectedStatus" />
            <span>{{ 'compliance.resolve_dialog.dismiss_option' | t }}</span>
          </label>
          <label class="radio-option">
            <input type="radio" name="status" value="ESCALATED" [(ngModel)]="selectedStatus" />
            <span>{{ 'compliance.resolve_dialog.escalate_option' | t }}</span>
          </label>
        </div>

        <app-form-field [label]="'compliance.resolve_dialog.notes_label' | t" class="notes-field">
          <textarea rows="4" [(ngModel)]="notes" class="form-input min-h-[100px]"></textarea>
        </app-form-field>
      </div>
      <div class="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
        <button class="btn-outline" (click)="cancel()">{{ 'compliance.resolve_dialog.cancel_action' | t }}</button>
        <button class="btn-primary" (click)="confirm()" [disabled]="!canConfirm()">
          {{ 'compliance.resolve_dialog.confirm_action' | t }}
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .alert-ref {
        margin-bottom: 1rem;
        color: rgba(0, 0, 0, 0.6);
      }

      .radio-group {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-bottom: 1rem;
      }

      .radio-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 0.375rem;
        transition: background-color 0.2s;
      }

      .radio-option:hover {
        background-color: #f8fafc;
      }

      .radio-option input[type="radio"] {
        cursor: pointer;
        width: 1rem;
        height: 1rem;
      }

      .radio-option span {
        font-size: 0.875rem;
      }

      .notes-field {
        width: 100%;
      }
    `,
  ],
})
export class ResolveAlertDialogComponent {
  selectedStatus: 'DISMISSED' | 'ESCALATED' | null = null;
  notes = '';

  constructor(
    private dialogRef: DialogRef<DialogResult | undefined>,
    @Inject(DIALOG_DATA) public data: DialogData,
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

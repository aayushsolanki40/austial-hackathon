import { Component, Input } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';

/**
 * Generic status badge with configurable color mapping. Used for AML alert status,
 * report status, etc.
 */
@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [MatChipsModule],
  template: `<mat-chip [class]="'status-chip status-chip--' + colorClass">{{ status }}</mat-chip>`,
  styles: [
    `
      .status-chip {
        font-weight: 500;
        font-size: 0.75rem;
      }

      .status-chip--success {
        background-color: #4caf50;
        color: white;
      }

      .status-chip--warning {
        background-color: #ff9800;
        color: white;
      }

      .status-chip--error {
        background-color: #f44336;
        color: white;
      }

      .status-chip--info {
        background-color: #2196f3;
        color: white;
      }

      .status-chip--default {
        background-color: #757575;
        color: white;
      }
    `,
  ],
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: string;
  @Input() colorClass: 'success' | 'warning' | 'error' | 'info' | 'default' = 'default';
}

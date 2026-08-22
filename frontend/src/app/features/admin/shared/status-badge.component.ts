import { Component, Input } from '@angular/core';

/**
 * Generic status badge with configurable color mapping. Used for AML alert status,
 * report status, etc.
 */
@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `<span class="badge" [class]="badgeClass()">{{ status }}</span>`,
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: string;
  /** Kept as `colorClass` (rather than renamed) -- bound by name from the deferred
   * MatTable call sites (`report-generator`/`aml-alert-queue`), which this pass leaves
   * untouched. */
  @Input() colorClass: 'success' | 'warning' | 'error' | 'info' | 'default' = 'default';

  badgeClass(): string {
    const colorMap: Record<string, string> = {
      success: 'badge-success',
      warning: 'badge-warning',
      error: 'badge-error',
      info: 'badge-info',
      default: 'bg-slate-100 text-slate-700',
    };
    return colorMap[this.colorClass] ?? colorMap['default'];
  }
}

import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Tailwind-styled form field wrapper to replace MatFormField.
 * Provides label, input container, hint, and error display.
 */
@Component({
  selector: 'app-form-field',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="form-group">
      @if (label) {
        <label [attr.for]="inputId" class="form-label">{{ label }}</label>
      }
      <ng-content />
      @if (hint && !error) {
        <p class="text-sm text-slate-500 mt-1">{{ hint }}</p>
      }
      @if (error) {
        <p class="form-error">{{ error }}</p>
      }
    </div>
  `,
})
export class FormFieldComponent {
  @Input() label?: string;
  @Input() hint?: string;
  @Input() error?: string;
  @Input() inputId?: string;
}

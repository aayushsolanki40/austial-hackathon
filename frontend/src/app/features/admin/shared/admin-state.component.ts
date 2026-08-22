import { Component, EventEmitter, Input, Output } from '@angular/core';

import { TPipe } from '../../../core/i18n/t.pipe';

/**
 * Loading/error state shared by `dashboard` and `users` -- the only two
 * admin sections that make a real API call today. Every other
 * `features/admin/` section is a static placeholder with nothing to load,
 * so this stays scoped to what those two actually need rather than growing
 * into a speculative generic "admin data state" component.
 */
@Component({
  selector: 'app-admin-state',
  standalone: true,
  imports: [TPipe],
  template: `
    @if (state === 'loading') {
      <div class="admin-state admin-state--loading">
        <img src="assets/images/logo/austial-icon.svg" alt="Loading" class="h-8 animate-pulse" />
        <span>{{ 'admin.state.loading' | t }}</span>
      </div>
    } @else {
      <div class="admin-state admin-state--error">
        <p>{{ 'admin.state.error' | t }}</p>
        <button class="btn-outline" (click)="retry.emit()">{{ 'admin.state.retry' | t }}</button>
      </div>
    }
  `,
  styles: [
    `
      .admin-state {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1.5rem 0;
      }

      .admin-state--error {
        flex-direction: column;
        align-items: flex-start;
      }

      .admin-state--error p {
        margin: 0;
        color: rgba(0, 0, 0, 0.6);
      }
    `,
  ],
})
export class AdminStateComponent {
  @Input({ required: true }) state!: 'loading' | 'error';
  @Output() readonly retry = new EventEmitter<void>();
}

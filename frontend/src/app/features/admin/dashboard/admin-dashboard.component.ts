import { DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';

import { ApiService } from '../../../core/api/api.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { AdminDashboardSummary } from '../admin.models';
import { AdminStateComponent } from '../shared/admin-state.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * KPI overview: AUM, investor count, active issuances, pending KYC, open
 * AML alerts. Calls `GET /admin/dashboard/summary` -- that backend endpoint
 * doesn't exist yet (Section 1.5's `modules/admin/` is separate in-flight
 * work), so this renders `AdminStateComponent`'s error state with a retry
 * button until it ships, rather than fabricating numbers.
 */
@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [MatCardModule, AdminStateComponent, TPipe, DecimalPipe],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss',
})
export default class AdminDashboardComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly state = signal<LoadState>('loading');
  readonly summary = signal<AdminDashboardSummary | null>(null);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.api.get<AdminDashboardSummary>('/admin/dashboard/summary').subscribe({
      next: (summary) => {
        this.summary.set(summary);
        this.state.set('loaded');
      },
      error: () => this.state.set('error'),
    });
  }
}

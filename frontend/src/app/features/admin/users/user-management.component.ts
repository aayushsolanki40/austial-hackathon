import { Component, OnInit, inject, signal } from '@angular/core';
import { MatTableModule } from '@angular/material/table';

import { ApiService } from '../../../core/api/api.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { AdminUserSummary } from '../admin.models';
import { AdminStateComponent } from '../shared/admin-state.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Search/list users, ADMIN-only (see `admin.routes.ts`'s per-route
 * `roleGuard(['ADMIN'])`). Calls `GET /admin/users` -- role
 * assignment/suspend actions (`PATCH /admin/users/:id/role`,
 * `PATCH /admin/users/:id/suspend`) are Section 1.5 backend work that
 * hasn't shipped yet, so this is read-only for now: list + graceful
 * loading/error state, no mutation UI ahead of the endpoints existing.
 */
@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [MatTableModule, AdminStateComponent, TPipe],
  templateUrl: './user-management.component.html',
  styleUrl: './user-management.component.scss',
})
export default class UserManagementComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly state = signal<LoadState>('loading');
  readonly users = signal<AdminUserSummary[]>([]);
  readonly displayedColumns = ['email', 'role', 'status', 'created_at'];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.api.get<AdminUserSummary[]>('/admin/users').subscribe({
      next: (users) => {
        this.users.set(users);
        this.state.set('loaded');
      },
      error: () => this.state.set('error'),
    });
  }
}

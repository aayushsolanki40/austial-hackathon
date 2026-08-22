import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';

import { ApiService } from '../../../core/api/api.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { KycReviewQueueItem, KycReviewQueueResponse } from '../admin.models';
import { AdminStateComponent } from '../shared/admin-state.component';
import { FormFieldComponent } from '../../../shared/components/form-field/form-field.component';

type LoadState = 'loading' | 'error' | 'loaded';

const PAGE_SIZE = 50;

/**
 * Compliance Officer KYC review queue -- gated by the parent `/admin` route's
 * `roleGuard(['COMPLIANCE_OFFICER', 'ADMIN'])` (see `admin.routes.ts`), no
 * additional per-route guard needed here.
 *
 * Calls the real `KycController` review endpoints (`backend/src/modules/kyc/kyc_controller.py`):
 * `GET /kyc/review-queue?skip=&take=`, `POST /kyc/submissions/:id/approve`,
 * `POST /kyc/submissions/:id/reject`. The queue only ever contains submissions in
 * `MANUAL_REVIEW` (the backend's `list_pending_review` filters on exactly that status), so
 * every row here is actionable.
 *
 * Rejection requires a reason (stored server-side as `review_notes`), so each row tracks
 * its own free-text reason input via `rejectReasons` rather than a single shared form
 * field -- multiple rows can be mid-review at once without clobbering each other's draft
 * reason.
 */
@Component({
  selector: 'app-kyc-review-queue',
  standalone: true,
  imports: [MatTableModule, MatButtonModule, AdminStateComponent, FormFieldComponent, TPipe],
  templateUrl: './kyc-review-queue.component.html',
  styleUrl: './kyc-review-queue.component.scss',
})
export default class KycReviewQueueComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly state = signal<LoadState>('loading');
  readonly queue = signal<KycReviewQueueItem[]>([]);
  readonly rejectReasons = signal<Record<number, string>>({});
  readonly actioningId = signal<number | null>(null);
  readonly displayedColumns = ['investor_id', 'legal_name', 'nationality', 'status', 'submitted_at', 'actions'];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.api.get<KycReviewQueueResponse>('/kyc/review-queue', { skip: 0, take: PAGE_SIZE }).subscribe({
      next: (response) => {
        this.queue.set(response.items);
        this.state.set('loaded');
      },
      error: () => this.state.set('error'),
    });
  }

  reasonFor(submissionId: number): string {
    return this.rejectReasons()[submissionId] ?? '';
  }

  setReason(submissionId: number, reason: string): void {
    this.rejectReasons.update((reasons) => ({ ...reasons, [submissionId]: reason }));
  }

  approve(item: KycReviewQueueItem): void {
    this.actioningId.set(item.id);
    this.api.post<void>(`/kyc/submissions/${item.id}/approve`).subscribe({
      next: () => {
        this.actioningId.set(null);
        this.removeFromQueue(item.id);
      },
      error: () => this.actioningId.set(null),
    });
  }

  reject(item: KycReviewQueueItem): void {
    const reason = this.reasonFor(item.id).trim();
    if (!reason) {
      return;
    }
    this.actioningId.set(item.id);
    this.api.post<void>(`/kyc/submissions/${item.id}/reject`, { reason }).subscribe({
      next: () => {
        this.actioningId.set(null);
        this.removeFromQueue(item.id);
      },
      error: () => this.actioningId.set(null),
    });
  }

  private removeFromQueue(submissionId: number): void {
    this.queue.update((items) => items.filter((item) => item.id !== submissionId));
  }
}

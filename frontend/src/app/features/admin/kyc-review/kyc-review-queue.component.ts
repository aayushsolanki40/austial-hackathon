import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 2's KYC review queue, surfaced in the admin shell per Section 1.5. */
@Component({
  selector: 'app-kyc-review-queue',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="admin.nav.kyc_review" messageKey="admin.placeholder.kyc_review" />`,
})
export default class KycReviewQueueComponent {}

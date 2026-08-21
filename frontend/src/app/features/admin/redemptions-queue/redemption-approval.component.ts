import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 7's redemption approval queue. */
@Component({
  selector: 'app-redemption-approval',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="admin.nav.redemptions" messageKey="admin.placeholder.redemptions" />`,
})
export default class RedemptionApprovalComponent {}

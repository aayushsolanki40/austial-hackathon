import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 7's redemption request flow (`/holdings/:id/redeem`). */
@Component({
  selector: 'app-holding-redeem',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="portfolio.holding_redeem.title"
    messageKey="portfolio.holding_redeem.placeholder"
  />`,
})
export default class HoldingRedeemComponent {}

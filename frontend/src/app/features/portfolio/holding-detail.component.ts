import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 6's holding detail (`/holdings/:id`). */
@Component({
  selector: 'app-holding-detail',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="portfolio.holding_detail.title"
    messageKey="portfolio.holding_detail.placeholder"
  />`,
})
export default class HoldingDetailComponent {}

import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 6's marketplace (asset-class filters, browse tokenized assets). */
@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="marketplace.list.title" messageKey="marketplace.list.placeholder" />`,
})
export default class MarketplaceComponent {}

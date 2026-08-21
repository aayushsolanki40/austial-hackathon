import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 6's subscription flow (`/assets/:id/subscribe`). */
@Component({
  selector: 'app-asset-subscribe',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="marketplace.asset_subscribe.title"
    messageKey="marketplace.asset_subscribe.placeholder"
  />`,
})
export default class AssetSubscribeComponent {}

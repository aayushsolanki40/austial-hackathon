import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 6's asset detail + prospectus viewer (`/assets/:id`). */
@Component({
  selector: 'app-asset-detail',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="marketplace.asset_detail.title"
    messageKey="marketplace.asset_detail.placeholder"
  />`,
})
export default class AssetDetailComponent {}

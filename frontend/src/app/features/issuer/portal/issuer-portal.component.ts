import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for the Phase 3/4 issuer portal shell (asset submission form, dynamic fields per asset class). */
@Component({
  selector: 'app-issuer-portal',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="issuer.portal.title" messageKey="issuer.portal.placeholder" />`,
})
export default class IssuerPortalComponent {}

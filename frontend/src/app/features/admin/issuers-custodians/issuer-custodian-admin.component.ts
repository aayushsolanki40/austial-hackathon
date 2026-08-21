import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 3's issuer approval + custodian IFSCA-registry verification. */
@Component({
  selector: 'app-issuer-custodian-admin',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="admin.nav.issuers_custodians"
    messageKey="admin.placeholder.issuers_custodians"
  />`,
})
export default class IssuerCustodianAdminComponent {}

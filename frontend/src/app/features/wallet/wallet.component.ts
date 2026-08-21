import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 5's wallet/funding page (`/wallet`). */
@Component({
  selector: 'app-wallet',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="wallet.overview.title" messageKey="wallet.overview.placeholder" />`,
})
export default class WalletComponent {}

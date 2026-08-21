import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 6's portfolio dashboard (`/portfolio`). */
@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="portfolio.overview.title" messageKey="portfolio.overview.placeholder" />`,
})
export default class PortfolioComponent {}

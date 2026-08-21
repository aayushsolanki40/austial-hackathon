import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 8's quarterly IFSCA report generator (AUM, currency breakdown, etc). */
@Component({
  selector: 'app-report-generator',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="admin.nav.compliance"
    messageKey="admin.placeholder.report_generator"
  />`,
})
export default class ReportGeneratorComponent {}

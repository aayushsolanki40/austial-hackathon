import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 4's issuance kanban, disclosure checklist, circuit-breaker control. */
@Component({
  selector: 'app-issuance-pipeline',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page
    titleKey="admin.nav.issuance_pipeline"
    messageKey="admin.placeholder.issuance_pipeline"
  />`,
})
export default class IssuancePipelineComponent {}

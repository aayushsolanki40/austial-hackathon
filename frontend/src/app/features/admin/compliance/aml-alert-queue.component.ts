import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 8's AML alert queue with resolution workflow. */
@Component({
  selector: 'app-aml-alert-queue',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="admin.nav.compliance" messageKey="admin.placeholder.compliance" />`,
})
export default class AmlAlertQueueComponent {}

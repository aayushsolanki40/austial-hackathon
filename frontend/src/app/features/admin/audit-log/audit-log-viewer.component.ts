import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/** Placeholder for Phase 8's immutable AuditLog viewer. */
@Component({
  selector: 'app-audit-log-viewer',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="admin.nav.audit_log" messageKey="admin.placeholder.audit_log" />`,
})
export default class AuditLogViewerComponent {}

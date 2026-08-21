import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { TPipe } from '../../../core/i18n/t.pipe';

interface AdminNavLink {
  path: string;
  labelKey: string;
  icon: string;
  /** Section 1.5: `users` is ADMIN-only, unlike every other admin section (shared by
   * COMPLIANCE_OFFICER + ADMIN). Hiding the link for a role that would just get bounced
   * by `roleGuard(['ADMIN'])` on `admin/users` avoids a dead-end nav item. */
  adminOnly?: boolean;
}

const NAV_LINKS: AdminNavLink[] = [
  { path: 'dashboard', labelKey: 'admin.nav.dashboard', icon: 'dashboard' },
  { path: 'users', labelKey: 'admin.nav.users', icon: 'group', adminOnly: true },
  { path: 'kyc-review', labelKey: 'admin.nav.kyc_review', icon: 'fact_check' },
  { path: 'issuers-custodians', labelKey: 'admin.nav.issuers_custodians', icon: 'domain' },
  { path: 'issuance-pipeline', labelKey: 'admin.nav.issuance_pipeline', icon: 'view_kanban' },
  { path: 'valuation-oracle', labelKey: 'admin.nav.valuation_oracle', icon: 'monitoring' },
  { path: 'redemptions', labelKey: 'admin.nav.redemptions', icon: 'undo' },
  { path: 'compliance', labelKey: 'admin.nav.compliance', icon: 'gavel' },
  { path: 'audit-log', labelKey: 'admin.nav.audit_log', icon: 'history' },
];

/**
 * Sidenav layout wrapping every `features/admin/` section (Section 1.5).
 * Sections light up incrementally as their owning phase ships; the shell
 * itself is Phase 1.10, built now.
 */
@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatToolbarModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    TPipe,
  ],
  templateUrl: './admin-shell.component.html',
  styleUrl: './admin-shell.component.scss',
})
export default class AdminShellComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly navLinks = computed(() => NAV_LINKS.filter((link) => !link.adminOnly || this.auth.role() === 'ADMIN'));

  async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/login');
  }
}

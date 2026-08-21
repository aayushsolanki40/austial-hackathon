import { Component, Input } from '@angular/core';

import { TPipe } from '../../core/i18n/t.pipe';

/**
 * Minimal "coming in Phase N" empty state, reused by every route stubbed
 * ahead of its owning build-plan phase (KYC onboarding, marketplace,
 * portfolio, wallet, issuer portal, and most `features/admin/` sections).
 * Titles/messages are always looked up via `I18nService`/`TPipe` -- never
 * pass literal copy through these inputs, pass an i18n key.
 */
@Component({
  selector: 'app-placeholder-page',
  standalone: true,
  imports: [TPipe],
  template: `
    <section class="placeholder-page">
      <h1>{{ titleKey | t }}</h1>
      <p>{{ messageKey | t }}</p>
    </section>
  `,
  styles: [
    `
      .placeholder-page {
        padding: 2rem;
        max-width: 640px;
      }

      h1 {
        margin: 0 0 0.5rem;
        font-size: 1.5rem;
      }

      p {
        margin: 0;
        color: rgba(0, 0, 0, 0.6);
      }
    `,
  ],
})
export class PlaceholderPageComponent {
  @Input({ required: true }) titleKey!: string;
  @Input({ required: true }) messageKey!: string;
}

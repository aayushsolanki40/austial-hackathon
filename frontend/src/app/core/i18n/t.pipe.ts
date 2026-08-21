import { Pipe, PipeTransform, inject } from '@angular/core';

import { I18nService } from './i18n.service';

/**
 * Template-facing wrapper over `I18nService.t()`: `{{ 'admin.dashboard.title' | t }}`.
 * Pure (default) so it only re-evaluates when the input key changes.
 */
@Pipe({ name: 't', standalone: true })
export class TPipe implements PipeTransform {
  private readonly i18n = inject(I18nService);

  transform(key: string): string {
    return this.i18n.t(key);
  }
}

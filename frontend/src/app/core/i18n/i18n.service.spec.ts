import { TestBed } from '@angular/core/testing';

import { I18nService } from './i18n.service';

describe('I18nService', () => {
  let service: I18nService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(I18nService);
  });

  it('resolves a flat top-level key', () => {
    expect(service.t('app.title')).toBe('Swadely');
  });

  it('resolves a one-level-nested key as module.key.subkey', () => {
    expect(service.t('admin.dashboard.title')).toBe('Dashboard');
  });

  it('falls back to the key itself and logs an error for a missing key', () => {
    spyOn(console, 'error');
    expect(service.t('app.nonexistent_key')).toBe('app.nonexistent_key');
    expect(console.error).toHaveBeenCalled();
  });
});

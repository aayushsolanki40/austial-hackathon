import { Injectable } from '@angular/core';

import adminEn from '../../../i18n/locales/en/admin.json';
import appEn from '../../../i18n/locales/en/app.json';
import assetEn from '../../../i18n/locales/en/asset.json';
import authEn from '../../../i18n/locales/en/auth.json';
import custodianEn from '../../../i18n/locales/en/custodian.json';
import issuanceEn from '../../../i18n/locales/en/issuance.json';
import issuerEn from '../../../i18n/locales/en/issuer.json';
import kycEn from '../../../i18n/locales/en/kyc.json';
import marketplaceEn from '../../../i18n/locales/en/marketplace.json';
import portfolioEn from '../../../i18n/locales/en/portfolio.json';
import redemptionsEn from '../../../i18n/locales/en/redemptions.json';
import valuationEn from '../../../i18n/locales/en/valuation.json';
import walletEn from '../../../i18n/locales/en/wallet.json';

/** One module's locale JSON: flat string values, or one level of nesting. */
type LocaleModule = Record<string, string | Record<string, string>>;

const DEFAULT_LOCALE = 'en';

/**
 * Registry of every module's locale JSON, per locale. Mirrors
 * `backend/src/i18n/locales/<locale>/<module>.json` -- one file per app
 * module per locale (see `frontend/src/i18n/README.md`). Add a new module's
 * import + registry entry here whenever a new `features/<domain>/` needs
 * user-facing strings.
 */
const LOCALE_MODULES: Record<string, Record<string, LocaleModule>> = {
  en: {
    app: appEn,
    auth: authEn,
    admin: adminEn,
    kyc: kycEn,
    marketplace: marketplaceEn,
    portfolio: portfolioEn,
    wallet: walletEn,
    issuer: issuerEn,
    asset: assetEn,
    custodian: custodianEn,
    issuance: issuanceEn,
    valuation: valuationEn,
    redemptions: redemptionsEn,
  },
};

/**
 * Flattens every module's JSON for `locale` into a single lookup table
 * namespaced by `<module>.<key>` (and `<module>.<key>.<subKey>` for one
 * level of nesting) -- the exact merge algorithm `backend/src/i18n/i18n.py`
 * uses, so call sites use a flat key (`t('auth.error.generic')`) regardless
 * of the file split.
 */
function buildLookup(locale: string): Record<string, string> {
  const modules = LOCALE_MODULES[locale];
  if (!modules) {
    throw new Error(`No i18n locale modules registered for locale "${locale}"`);
  }

  const strings: Record<string, string> = {};
  for (const [moduleName, moduleStrings] of Object.entries(modules)) {
    for (const [key, value] of Object.entries(moduleStrings)) {
      if (typeof value === 'string') {
        strings[`${moduleName}.${key}`] = value;
      } else {
        for (const [subKey, subValue] of Object.entries(value)) {
          strings[`${moduleName}.${key}.${subKey}`] = subValue;
        }
      }
    }
  }
  return strings;
}

const lookupCache = new Map<string, Record<string, string>>();

function lookupFor(locale: string): Record<string, string> {
  let lookup = lookupCache.get(locale);
  if (!lookup) {
    lookup = buildLookup(locale);
    lookupCache.set(locale, lookup);
  }
  return lookup;
}

/**
 * i18n loader implementing the backend's `t("module.key")` convention on
 * the frontend. Locale JSON is bundled at build time (no runtime HTTP
 * fetch), so lookups are synchronous and safe to call from guards/services
 * as well as templates (via `TPipe`).
 *
 * Per the workspace hard rule, no user-facing string literal belongs
 * inline in component/service source -- route it through `t()` and a
 * module locale JSON file instead.
 */
@Injectable({ providedIn: 'root' })
export class I18nService {
  private locale = DEFAULT_LOCALE;

  setLocale(locale: string): void {
    this.locale = locale;
  }

  getLocale(): string {
    return this.locale;
  }

  /** Look up `key` (e.g. `"admin.dashboard.title"`) in the active locale. */
  t(key: string): string {
    const value = lookupFor(this.locale)[key];
    if (value === undefined) {
      // Fail loudly in dev rather than silently rendering "undefined" --
      // mirrors the backend loader raising `KeyError` on a missing key.
      console.error(`Missing i18n key "${key}" for locale "${this.locale}"`);
      return key;
    }
    return value;
  }
}

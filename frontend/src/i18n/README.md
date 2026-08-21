# i18n locale files

Convention (per workspace `CLAUDE.md`): one JSON file per app module per
locale, mirroring `src/app/<domain>/` as domain modules (payments,
tokenization, KYC, wallet, compliance-reporting, etc.) are added — not one
giant flat file per locale.

```
src/i18n/locales/<locale>/<module>.json
```

e.g. `src/i18n/locales/en/app.json`, `src/i18n/locales/en/kyc.json`,
`src/i18n/locales/en/wallet.json`.

A project-conventional loader should merge all module files for a given
locale into one lookup namespaced by `<module>.<key>` (e.g.
`t("kyc.status.pending_review")`), so call sites use a flat key regardless
of the file split. No loader/pipe/service has been implemented yet — this
is only the folder convention scaffold. Wire up an actual loader (e.g. an
Angular `TranslateService`-style provider reading these JSON files, or
`@angular/localize` if full i18n compile-time extraction is preferred later)
when the first real domain module needing user-facing strings is built, per
`api.swadely.com/src/i18n/` as the reference implementation.

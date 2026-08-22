# Frontend session memory — Angular Material removal

Working notes for an in-progress task, kept so the session can resume after
the Claude usage limit reset (hit limit ~2026-08-22, resets 2pm Asia/Calcutta).
Delete this file once the task below is fully complete and verified.

## Stack correction (important, differs from root CLAUDE.md)

`austial-hackathon/frontend/` is **Angular 19** (Angular Material, RxJS,
standalone components, signals) — NOT React/Vite/TanStack Query/Zustand as
the root `CLAUDE.md` folder-map table currently says. No React code exists
in this directory. Root CLAUDE.md should be corrected at some point; not
done yet.

Tailwind 3.4.17 is already correctly configured and working:
- `tailwind.config.js` wired into `angular.json`
- `src/styles.scss` imports Tailwind directives + defines 15+ reusable
  component classes: `.card`, `.btn-primary`/`.btn-secondary`/`.btn-outline`,
  `.form-group`/`.form-input`/`.form-error`, `.table`/`.table-container`,
  `.badge`, `.spinner`, `.status-dot`.

## Original bug that started this thread

`POST /investors/profile` was returning 403 for a user with an ISSUER JWT
hitting an INVESTOR-only backend endpoint (`@Roles("INVESTOR")` on
`investors_controller.py:31`). Root cause was a **frontend role-guard gap**,
not a backend bug — fixed already (see "Completed: role guard fixes" below).

## Completed: role guard fixes (done, verified, not yet redeployed)

- `app.routes.ts`: added `roleGuard(['INVESTOR'])` to `/onboarding` and
  `/app` (both were only behind `authGuard`, letting any logged-in role
  reach INVESTOR-only API calls).
- `admin.routes.ts`: added `roleGuard(['COMPLIANCE_OFFICER'])` to
  `kyc-review` and `issuers-custodians` (parent `/admin` route allows both
  ADMIN and COMPLIANCE_OFFICER in, but these two sub-routes' backend
  endpoints are COMPLIANCE_OFFICER-only).
- `admin-shell.component.ts`: added `complianceOnly` nav-link flag so ADMIN
  users don't see links they can't use.
- New `core/auth/post-auth-redirect.ts`: `postAuthRedirectUrl(role, opts)`
  routes each role to its correct home after register/login instead of a
  hardcoded `/onboarding` redirect for everyone.
- `register.component.ts` / `login.component.ts`: use
  `postAuthRedirectUrl(...)` now.
- Confirmed via backend read: `POST /auth/register` hardcodes
  `role="INVESTOR"` on every self-registration; ISSUER/COMPLIANCE_OFFICER/
  ADMIN are only assignable via `PATCH /admin/users/:id/role` by an existing
  admin. No self-service issuer/admin signup exists — no role-picker UI was
  needed or built.
- `ng build` was clean after this pass.
- **Not yet redeployed** — this is a frontend-only change (no new AWS
  resource, no Terraform delta) but the live S3 bucket still serves the old
  bundle. Rebuild+redeploy via `austial-infra-sync` agent still pending —
  user has not yet confirmed they want this pushed live.

## COMPLETED: Angular Material removal (moderate + complex tiers)

User's ask: "remove material design entirely, because sometime tailwind is
not implementing." Diagnosis: Angular Material's own component CSS + the
prebuilt theme (`@angular/material/prebuilt-themes/indigo-pink.css` in
`angular.json`) has higher specificity than Tailwind and silently overrides
it in places — not a Tailwind config problem.

**Status:** Moderate and complex tiers complete and committed (5639db1).
Trivial tier was already done. MatTable migration explicitly deferred.

### Scope audit result (confirmed via Explore agent)

36 files import Angular Material across ~20 modules. Breakdown:
- **Trivial** (~22 files): MatButton(31), MatProgressSpinner(21),
  MatInput(18), MatCard(15), MatIcon(5), MatCheckbox(3), MatRadio(2),
  MatProgressBar(2), MatCore(2), MatChips(2), MatToolbar(1),
  MatSlideToggle(1), MatList(1) — replace with native HTML + existing
  Tailwind classes.
- **Moderate** (~8 files): MatFormField(19), MatSelect(9), MatTabs(1),
  MatStepper(1), MatSidenav(1) — need small reusable Tailwind-styled
  standalone components.
- **Complex, in scope** (~6 files): MatDialog(4), MatDatepicker(2).
- **Explicitly OUT OF SCOPE / deferred to a separate follow-up task**:
  **MatTable (14 files)** — sorting/pagination logic, left on Material for
  now. Do not touch these files in this pass. `@angular/material` and
  `@angular/cdk` package.json deps, and the Material theme CSS in
  `angular.json`, **must stay** until the table follow-up is done, since
  these 14 files still depend on them.

### User decisions locked in (do not re-ask)

1. **Dialog/datepicker mechanics**: keep `@angular/cdk` (drop only
   `@angular/material`) — use `@angular/cdk/dialog` and/or
   `@angular/cdk/overlay` (unstyled/headless) for overlay + focus-trap +
   positioning, styled entirely with Tailwind.
2. **Tables**: defer all 14 MatTable files to a separate follow-up task —
   not part of this pass.
3. **Rollout**: one full pass covering trivial + moderate + complex
   (non-table) files, single report at the end (not staged).

### Completed work (committed as 5639db1)

**Trivial tier** (30 files, already done before 2026-08-22 session):
- MatButton, MatCard, MatIcon, MatProgressSpinner, MatCheckbox, MatRadio replacements
- Created `shared/components/icon/icon.component.ts` with hand-authored SVG paths

**Moderate tier** (14 files, completed 2026-08-22):
- Created 4 new shared components: form-field/, select/, tabs/, stepper/
- Migrated MatFormField/MatInput → app-form-field + native inputs (13 files)
- Migrated MatSelect → app-select with ControlValueAccessor (7 files)
- Migrated MatTabGroup → app-tabs (redemption-approval)
- Migrated MatStepper → app-stepper (onboarding, 5 steps)

**Complex tier** (6 files, completed 2026-08-22):
- Migrated MatDialog → @angular/cdk/dialog + Tailwind (2 dialogs, 2 openers)
- Migrated MatDatepicker → native HTML5 date inputs (4 fields, 2 components)
- Added CDK overlay styles to styles.scss

**Total migration:** 33 files changed (+870/-464 lines), 6 new components created.
Build verified successful: 464KB initial bundle, 3.3s build time.

### Next steps (if user wants to continue)

1. **MatTable migration** (14 files, explicitly deferred) — this is a
   separate, larger task. Options: keep Material tables, migrate to Tailwind
   + custom sorting/pagination, or adopt a headless table library.
2. **Remove Material dependencies** — after MatTable migration is complete,
   remove `@angular/material` from `package.json` and the Material theme CSS
   from `angular.json`. Keep `@angular/cdk` (used by dialog system).
3. **Redeploy to AWS** — trigger `austial-infra-sync` / `sync-aws-infra` to
   rebuild and redeploy frontend to S3. This Material removal + the earlier
   role-guard fixes are both frontend-only changes (no Terraform delta), but
   the live S3 bucket needs the new build pushed.

File can be deleted once user confirms no further Material work is needed.

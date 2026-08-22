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

## In progress: remove Angular Material entirely (Tailwind fights Material CSS)

User's ask: "remove material design entirely, because sometime tailwind is
not implementing." Diagnosis: Angular Material's own component CSS + the
prebuilt theme (`@angular/material/prebuilt-themes/indigo-pink.css` in
`angular.json`) has higher specificity than Tailwind and silently overrides
it in places — not a Tailwind config problem.

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

### Actual progress so far (per `git status` in `austial-hackathon/`, as of hitting the usage limit)

The implementation agent got through the **trivial** tier (buttons, cards,
icons, progress/spinners) across these files before hitting the Claude
usage limit mid-task — work is uncommitted, sitting as local changes:

Modified (30 files, +498/-639 lines):
- `features/admin/admin-shell/admin-shell.component.{html,ts}`
- `features/admin/dashboard/admin-dashboard.component.{html,ts}`
- `features/admin/issuance-pipeline/issuance-pipeline.component.{html,ts}`
- `features/admin/issuance-pipeline/proposal-review.component.{html,ts}`
- `features/admin/shared/admin-state.component.ts`
- `features/admin/shared/role-badge.component.ts`
- `features/admin/shared/status-badge.component.ts`
- `features/auth/login/login.component.ts`
- `features/auth/register/register.component.ts`
- `features/issuer/proposals/proposal-detail.component.{html,ts}`
- `features/kyc/onboarding/steps/document-upload-step/*.{html,ts}`
- `features/kyc/onboarding/steps/kyc-status-step/*.{html,ts}`
- `features/kyc/onboarding/steps/liveness-step/*.{html,ts}`
- `features/kyc/onboarding/steps/profile-step/*.{html,ts}`
- `features/kyc/onboarding/steps/risk-disclosure-step/*.{html,ts}`
- `features/marketplace/marketplace.component.ts`
- `features/portfolio/holding-detail.component.{html,ts}`
- `shared/disclosure-checklist/disclosure-checklist.component.{html,ts}`

New (untracked):
- `shared/components/icon/icon.component.ts` — new shared icon component
  (replaces MatIcon usage; check its approach — inline SVG vs icon set —
  before reusing the pattern elsewhere)

**Not started yet**: the moderate tier (MatFormField/MatInput wrapper,
MatSelect, MatTabs, MatStepper, MatSidenav, MatToolbar) and the complex tier
(MatDialog ×4 via `@angular/cdk/dialog`, MatDatepicker ×2). No `ng build`
verification run yet on this Material-removal work (the role-guard fixes
above were separately verified clean).

### Next steps to resume

1. Re-launch the `react-frontend-dev` agent (or continue inline) with this
   file as context. Verify the trivial-tier changes already made are
   correct first (`ng build`, spot-check a few migrated components) since
   they were never verified before the limit hit.
2. Continue with the moderate tier: build reusable Tailwind components
   under `shared/components/` (following `error-alert/`, `toast-container/`,
   `icon/` as precedent) for form-field wrapper, select/dropdown, tabs,
   stepper, sidenav.
3. Then the complex tier: MatDialog → `@angular/cdk/dialog` + Tailwind;
   MatDatepicker → `@angular/cdk/overlay` + Tailwind, custom calendar.
4. Do NOT touch the 14 MatTable files (list them explicitly by grepping
   `MatTableModule|MatTable` before starting, to confirm exact set).
5. Do NOT remove `@angular/material`/`@angular/cdk` from `package.json` or
   the theme CSS from `angular.json` yet — still required by the deferred
   table files.
6. Run `ng build` at the end to confirm clean build.
7. Once this pass + the role-guard fixes are both done and verified, ask
   user whether to trigger `austial-infra-sync` rebuild+redeploy to push
   everything live together.

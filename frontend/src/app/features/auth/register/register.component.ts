import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, Validators, NonNullableFormBuilder } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { postAuthRedirectUrl } from '../../../core/auth/post-auth-redirect';
import { TPipe } from '../../../core/i18n/t.pipe';
import { I18nService } from '../../../core/i18n/i18n.service';

/** Mirrors `RegisterDto` in `backend/src/modules/auth/auth_dto.py`: `Field(min_length=8)`. */
const PASSWORD_MIN_LENGTH = 8;

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, TPipe],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
})
export default class RegisterComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly i18n = inject(I18nService);

  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = this.fb.group({
    email: this.fb.control('', [Validators.required, Validators.email]),
    password: this.fb.control('', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH)]),
  });

  async submit(): Promise<void> {
    if (this.form.invalid || this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set(null);

    try {
      await this.auth.register(this.form.getRawValue());
      // `POST /auth/register` (`backend/src/modules/auth/auth_service.py`) always creates
      // an `INVESTOR`-role account today -- ISSUER/COMPLIANCE_OFFICER/ADMIN accounts only
      // exist via `PATCH /admin/users/:id/role`, there's no self-service role picker here.
      // Still route off the *actual* decoded role rather than hardcoding `/onboarding` so
      // this stays correct if that ever changes, and matches the same role-aware redirect
      // used post-login.
      await this.router.navigateByUrl(postAuthRedirectUrl(this.auth.role(), { justRegistered: true }));
    } catch (error: any) {
      const message =
        error?.userMessage ||
        error?.error?.message ||
        this.i18n.t('auth.error.generic');
      this.errorMessage.set(message);
    } finally {
      this.submitting.set(false);
    }
  }
}

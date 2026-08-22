import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { ToastService } from '../services/toast.service';

/**
 * Extracts user-friendly error messages from HTTP error responses.
 * Backend error shape (from Austial framework):
 * {
 *   statusCode: number;
 *   message: string;
 *   error: string;
 *   timestamp: string;
 *   path: string;
 * }
 */
function extractErrorMessage(error: HttpErrorResponse): string {
  if (error.error && typeof error.error === 'object') {
    if (error.error.message) {
      return error.error.message;
    }
  }

  if (error.message) {
    return error.message;
  }

  if (error.statusText) {
    return error.statusText;
  }

  return 'An unexpected error occurred. Please try again.';
}

/**
 * Global error interceptor that:
 * 1. Extracts backend error messages and attaches them to the error object as `userMessage`
 * 2. Shows toast notifications for certain error types (optional, can be controlled per-request)
 * 3. Lets components handle errors via catchError while ensuring consistent message extraction
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toastService = inject(ToastService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        const userMessage = extractErrorMessage(error);

        // Show toast for server errors (5xx) but let components handle client errors (4xx)
        // Components can still display inline errors for validation/auth failures
        if (error.status >= 500) {
          toastService.error(userMessage);
        }

        // Attach the extracted message to the error for component-level handling
        return throwError(() => ({
          ...error,
          userMessage,
        }));
      }

      return throwError(() => error);
    })
  );
};

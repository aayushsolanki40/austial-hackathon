/**
 * Development environment configuration.
 *
 * `ng serve` (default `development` configuration) uses this file as-is.
 * `ng build --configuration production` swaps it for `environment.prod.ts`
 * via the `fileReplacements` entry in `angular.json`.
 */
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000',
};

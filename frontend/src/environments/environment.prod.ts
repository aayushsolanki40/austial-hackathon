/**
 * Production environment configuration, swapped in for `environment.ts` by
 * the `fileReplacements` entry in `angular.json`'s `production` build
 * configuration.
 *
 * `apiBaseUrl` points at the deployed backend origin. Update alongside
 * `austial-hackathon/infra/terraform/` whenever the backend's public origin
 * changes (see root `CLAUDE.md` "AWS infra sync").
 */
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.swadely.com',
};

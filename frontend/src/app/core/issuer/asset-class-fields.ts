import { AssetClass } from './issuer.models';

/**
 * The real `CreateAssetDto` (`backend/src/modules/assets/assets_dto.py`) is just `name` +
 * `asset_class` + `description` -- there is no flexible `class_attributes` blob, so nothing
 * here is submitted to the API. What's left is purely client-side UX polish: an i18n hint
 * key shown under the description field once an `asset_class` is selected, nudging the
 * issuer to include the class-appropriate detail (a security's ISIN, a real estate asset's
 * location, etc.) in the one free-text field the backend actually stores.
 */
export const ASSET_CLASS_DESCRIPTION_HINTS: Record<AssetClass, string> = {
  SECURITY: 'issuer.asset_form_description_hint.security',
  REAL_ESTATE: 'issuer.asset_form_description_hint.real_estate',
  COMMODITY: 'issuer.asset_form_description_hint.commodity',
  INFRASTRUCTURE: 'issuer.asset_form_description_hint.infrastructure',
  IP: 'issuer.asset_form_description_hint.ip',
};

export const ASSET_CLASS_OPTIONS: { value: AssetClass; labelKey: string }[] = [
  { value: 'SECURITY', labelKey: 'asset.class_option.security' },
  { value: 'REAL_ESTATE', labelKey: 'asset.class_option.real_estate' },
  { value: 'COMMODITY', labelKey: 'asset.class_option.commodity' },
  { value: 'INFRASTRUCTURE', labelKey: 'asset.class_option.infrastructure' },
  { value: 'IP', labelKey: 'asset.class_option.ip' },
];

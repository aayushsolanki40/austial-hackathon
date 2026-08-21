import { AssetClass } from './issuer.models';

/** One dynamically-rendered `class_attributes` field for a given `AssetClass`. `key` is the
 * property name written into `Asset.class_attributes`/`CreateAssetRequest.class_attributes`. */
export interface AssetClassField {
  key: string;
  labelKey: string;
  type: 'text' | 'number';
  required: boolean;
}

/**
 * Per-asset-class dynamic field config for the issuer portal's asset submission form (build
 * plan Phase 3: "asset submission form (asset-class-specific dynamic fields)"). Deliberately
 * modest -- one or two fields that make a real difference to how each class is described,
 * not an attempt to model every possible attribute of five very different asset types. See
 * the ★ CONTRACT ASSUMPTION note on `Asset.class_attributes` in `issuer.models.ts` for why
 * this is a flexible key/value config rather than a discriminated union of typed DTOs.
 */
export const ASSET_CLASS_FIELDS: Record<AssetClass, AssetClassField[]> = {
  SECURITY: [
    { key: 'isin', labelKey: 'asset.field.isin', type: 'text', required: true },
    { key: 'issue_size', labelKey: 'asset.field.issue_size', type: 'text', required: false },
  ],
  REAL_ESTATE: [
    { key: 'property_location', labelKey: 'asset.field.property_location', type: 'text', required: true },
    { key: 'valuation_basis', labelKey: 'asset.field.valuation_basis', type: 'text', required: true },
  ],
  COMMODITY: [
    { key: 'commodity_type', labelKey: 'asset.field.commodity_type', type: 'text', required: true },
    { key: 'unit_of_measure', labelKey: 'asset.field.unit_of_measure', type: 'text', required: true },
  ],
  INFRASTRUCTURE: [
    { key: 'project_name', labelKey: 'asset.field.project_name', type: 'text', required: true },
    { key: 'concession_period_years', labelKey: 'asset.field.concession_period_years', type: 'number', required: false },
  ],
  IP: [
    { key: 'ip_type', labelKey: 'asset.field.ip_type', type: 'text', required: true },
    { key: 'registration_number', labelKey: 'asset.field.registration_number', type: 'text', required: true },
  ],
};

export const ASSET_CLASS_OPTIONS: { value: AssetClass; labelKey: string }[] = [
  { value: 'SECURITY', labelKey: 'asset.class_option.security' },
  { value: 'REAL_ESTATE', labelKey: 'asset.class_option.real_estate' },
  { value: 'COMMODITY', labelKey: 'asset.class_option.commodity' },
  { value: 'INFRASTRUCTURE', labelKey: 'asset.class_option.infrastructure' },
  { value: 'IP', labelKey: 'asset.class_option.ip' },
];

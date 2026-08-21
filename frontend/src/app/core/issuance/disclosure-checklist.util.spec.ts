import { buildDisclosureChecklist } from './disclosure-checklist.util';
import { DisclosureDocument } from './issuance.models';

function doc(overrides: Partial<DisclosureDocument> = {}): DisclosureDocument {
  return {
    id: 1,
    disclosure_type: 'RISK',
    object_key: 'disclosures/1/risk.pdf',
    version: 1,
    is_current: true,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildDisclosureChecklist', () => {
  it('marks every type missing per the server-supplied missing_disclosure_types list, even with matching documents present', () => {
    const allTypes = ['RISK', 'FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'];
    const checklist = buildDisclosureChecklist([], allTypes);
    expect(checklist.length).toBe(6);
    expect(checklist.every((item) => item.status === 'missing')).toBeTrue();
  });

  it('marks a type uploaded once it is absent from missing_disclosure_types', () => {
    const checklist = buildDisclosureChecklist([doc({ disclosure_type: 'RISK' })], ['FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS']);
    const risk = checklist.find((item) => item.type === 'RISK');
    expect(risk?.status).toBe('uploaded');
    expect(risk?.current?.disclosure_type).toBe('RISK');

    const fee = checklist.find((item) => item.type === 'FEE');
    expect(fee?.status).toBe('missing');
  });

  it('does not derive completeness from the disclosures array -- an empty missing list means every slot is uploaded regardless of documents', () => {
    const checklist = buildDisclosureChecklist([], []);
    expect(checklist.every((item) => item.status === 'uploaded')).toBeTrue();
  });

  it('picks the is_current document as current and treats the rest as history', () => {
    const older = doc({ id: 1, disclosure_type: 'PROSPECTUS', object_key: 'v1.pdf', version: 1, is_current: false, created_at: '2026-01-01T00:00:00Z' });
    const newer = doc({ id: 2, disclosure_type: 'PROSPECTUS', object_key: 'v2.pdf', version: 2, is_current: true, created_at: '2026-02-01T00:00:00Z' });

    const checklist = buildDisclosureChecklist([older, newer], []);
    const prospectus = checklist.find((item) => item.type === 'PROSPECTUS');

    expect(prospectus?.current?.object_key).toBe('v2.pdf');
    expect(prospectus?.history.map((d) => d.object_key)).toEqual(['v1.pdf']);
  });
});

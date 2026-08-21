import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { Holding } from '../../core/holdings/holdings.models';
import HoldingDetailComponent from './holding-detail.component';

function holding(overrides: Partial<Holding> = {}): Holding {
  return {
    id: 1,
    investor_id: 1,
    subscription_id: 1,
    token_series_id: 1,
    asset_name: 'Mumbai Commercial Tower',
    symbol: 'MCT',
    units: 10,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('HoldingDetailComponent', () => {
  let fixture: ComponentFixture<HoldingDetailComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HoldingDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: '1' }) } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HoldingDetailComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads the holding by id from the route via /holdings/mine/:id', fakeAsync(() => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/holdings/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(holding());
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.holding()?.units).toBe(10);
  }));

  it('falls back to the error state when the holding lookup fails', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/holdings/mine/1`).flush('not found', { status: 404, statusText: 'Not Found' });
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('error');
  }));
});

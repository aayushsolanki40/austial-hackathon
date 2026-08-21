import { Component, Input, computed, signal } from '@angular/core';

/** Minimal shape this chart needs -- callers pass `ValuationFeed[]` directly, no adapter needed. */
export interface NavChartPoint {
  reported_at: string;
  nav_per_unit: number;
}

const VIEW_WIDTH = 300;
const VIEW_HEIGHT = 100;
const VERTICAL_PADDING = 8;

/**
 * Dependency-light NAV sparkline: a self-contained inline SVG polyline, no charting library.
 * Renders nothing but a hint below two points (a single point has no trend to draw). Points are
 * sorted ascending by `reported_at` regardless of the order the caller passes them in.
 */
@Component({
  selector: 'app-nav-chart',
  standalone: true,
  template: `
    @if (points().length < 2) {
      <p class="nav-chart__hint">{{ hint }}</p>
    } @else {
      <svg [attr.viewBox]="'0 0 ' + width + ' ' + height" preserveAspectRatio="none" class="nav-chart__svg">
        <polyline [attr.points]="polylinePoints()" class="nav-chart__line" />
      </svg>
    }
  `,
  styles: [
    `
      .nav-chart__svg {
        width: 100%;
        height: 80px;
        display: block;
      }

      .nav-chart__line {
        fill: none;
        stroke: #3f51b5;
        stroke-width: 2;
        vector-effect: non-scaling-stroke;
      }

      .nav-chart__hint {
        color: rgba(0, 0, 0, 0.6);
        margin: 0;
      }
    `,
  ],
})
export class NavChartComponent {
  readonly width = VIEW_WIDTH;
  readonly height = VIEW_HEIGHT;

  @Input() hint = '';

  private readonly pointsSignal = signal<NavChartPoint[]>([]);
  @Input() set data(value: NavChartPoint[] | null | undefined) {
    this.pointsSignal.set(value ?? []);
  }

  readonly points = computed(() =>
    [...this.pointsSignal()].sort((a, b) => Date.parse(a.reported_at) - Date.parse(b.reported_at)),
  );

  readonly polylinePoints = computed(() => {
    const pts = this.points();
    const values = pts.map((p) => p.nav_per_unit);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = VIEW_WIDTH / (pts.length - 1);
    const drawableHeight = VIEW_HEIGHT - VERTICAL_PADDING * 2;

    return pts
      .map((p, index) => {
        const x = index * stepX;
        const y = VIEW_HEIGHT - VERTICAL_PADDING - ((p.nav_per_unit - min) / range) * drawableHeight;
        return `${x},${y}`;
      })
      .join(' ');
  });
}

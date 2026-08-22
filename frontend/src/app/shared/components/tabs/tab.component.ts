import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Individual tab to be used inside app-tabs.
 */
@Component({
  selector: 'app-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (active) {
      <div class="animate-fade-in">
        <ng-content />
      </div>
    }
  `,
  styles: [`
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .animate-fade-in {
      animation: fadeIn 0.2s ease-in;
    }
  `],
})
export class TabComponent {
  @Input() label = '';
  active = false;
}

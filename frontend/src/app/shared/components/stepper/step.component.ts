import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Individual step to be used inside app-stepper.
 */
@Component({
  selector: 'app-step',
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
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .animate-fade-in {
      animation: fadeIn 0.3s ease-out;
    }
  `],
})
export class StepComponent {
  @Input() label = '';
  @Input() completed = false;
  active = false;
}

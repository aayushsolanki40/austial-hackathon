import { Component, Input, Output, EventEmitter, ContentChildren, QueryList, AfterContentInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StepComponent } from './step.component';

/**
 * Tailwind-styled stepper component to replace MatStepper.
 * Provides horizontal step navigation with completed/active states.
 */
@Component({
  selector: 'app-stepper',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="stepper">
      <nav aria-label="Progress">
        <ol class="flex items-center">
          @for (step of steps; track step.label; let i = $index; let isLast = $last) {
            <li [class]="getStepItemClass(i, isLast)">
              <button
                type="button"
                (click)="selectStep(i)"
                [disabled]="linear && !canNavigateToStep(i)"
                [class]="getStepButtonClass(i)"
                [attr.aria-current]="selectedIndex === i ? 'step' : null"
              >
                <span class="flex items-center">
                  @if (step.completed) {
                    <span class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-600">
                      <svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    </span>
                  } @else {
                    <span [class]="getStepNumberClass(i)">
                      {{ i + 1 }}
                    </span>
                  }
                  <span class="ml-3 text-sm font-medium">{{ step.label }}</span>
                </span>
              </button>
              @if (!isLast) {
                <div [class]="getConnectorClass(i)" aria-hidden="true"></div>
              }
            </li>
          }
        </ol>
      </nav>
      <div class="mt-8">
        <ng-content />
      </div>
    </div>
  `,
  styles: [`
    .stepper {
      width: 100%;
    }
  `],
})
export class StepperComponent implements AfterContentInit {
  @Input() selectedIndex = 0;
  @Input() linear = false;
  @Output() selectedIndexChange = new EventEmitter<number>();

  @ContentChildren(StepComponent) steps!: QueryList<StepComponent>;

  ngAfterContentInit(): void {
    this.updateStepVisibility();
  }

  selectStep(index: number): void {
    if (this.linear && !this.canNavigateToStep(index)) {
      return;
    }
    this.selectedIndex = index;
    this.selectedIndexChange.emit(index);
    this.updateStepVisibility();
  }

  canNavigateToStep(index: number): boolean {
    if (!this.linear) return true;
    if (index <= this.selectedIndex) return true;
    const stepsArray = this.steps.toArray();
    for (let i = 0; i < index; i++) {
      if (!stepsArray[i]?.completed) return false;
    }
    return true;
  }

  private updateStepVisibility(): void {
    if (this.steps) {
      this.steps.forEach((step, i) => {
        step.active = i === this.selectedIndex;
      });
    }
  }

  getStepItemClass(index: number, isLast: boolean): string {
    return `relative ${isLast ? 'pr-0' : 'pr-8 sm:pr-20'} flex-1`;
  }

  getStepButtonClass(index: number): string {
    const base = 'group flex items-center transition-colors';
    const isDisabled = this.linear && !this.canNavigateToStep(index);
    if (isDisabled) {
      return `${base} cursor-not-allowed opacity-50`;
    }
    return `${base} cursor-pointer hover:opacity-80`;
  }

  getStepNumberClass(index: number): string {
    const base = 'flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium';
    if (index === this.selectedIndex) {
      return `${base} bg-primary-600 text-white`;
    }
    if (index < this.selectedIndex) {
      return `${base} bg-primary-100 text-primary-600`;
    }
    return `${base} border-2 border-slate-300 text-slate-500`;
  }

  getConnectorClass(index: number): string {
    const base = 'absolute top-4 -right-8 sm:-right-20 h-0.5 w-8 sm:w-20 transition-colors';
    const stepsArray = this.steps.toArray();
    if (stepsArray[index]?.completed) {
      return `${base} bg-primary-600`;
    }
    return `${base} bg-slate-300`;
  }
}

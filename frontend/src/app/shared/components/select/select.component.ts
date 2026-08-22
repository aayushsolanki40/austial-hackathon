import { Component, Input, Output, EventEmitter, forwardRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

export interface SelectOption {
  value: any;
  label: string;
}

/**
 * Tailwind-styled select dropdown to replace MatSelect.
 * Implements ControlValueAccessor for reactive forms integration.
 */
@Component({
  selector: 'app-select',
  standalone: true,
  imports: [CommonModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SelectComponent),
      multi: true,
    },
  ],
  template: `
    <div class="relative">
      <select
        [value]="value"
        (change)="onChange($event)"
        (blur)="onTouched()"
        [disabled]="disabled"
        [attr.aria-label]="ariaLabel"
        class="form-input appearance-none pr-10 cursor-pointer"
        [class.form-input-error]="hasError"
      >
        @if (placeholder) {
          <option value="" disabled [selected]="value === null || value === undefined">
            {{ placeholder }}
          </option>
        }
        @for (option of options; track option.value) {
          <option [value]="option.value">{{ option.label }}</option>
        }
      </select>
      <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-500">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </div>
    </div>
  `,
})
export class SelectComponent implements ControlValueAccessor {
  @Input() options: SelectOption[] = [];
  @Input() placeholder?: string;
  @Input() ariaLabel?: string;
  @Input() hasError = false;
  @Input() set value(val: any) {
    this._value = val;
  }
  get value(): any {
    return this._value;
  }
  @Output() selectionChange = new EventEmitter<any>();

  private _value: any = null;
  disabled = false;

  private _onChange: (value: any) => void = () => {};
  onTouched: () => void = () => {};

  onChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const newValue = target.value;
    this._value = newValue;
    this._onChange(newValue);
    this.selectionChange.emit(newValue);
  }

  writeValue(value: any): void {
    this._value = value;
  }

  registerOnChange(fn: (value: any) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }
}

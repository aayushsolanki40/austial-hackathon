import { Component, Input, Output, EventEmitter, ContentChildren, QueryList, AfterContentInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TabComponent } from './tab.component';

/**
 * Tailwind-styled tabs component to replace MatTabGroup.
 */
@Component({
  selector: 'app-tabs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="border-b border-slate-200">
      <nav class="flex space-x-4" aria-label="Tabs">
        @for (tab of tabs; track tab.label; let i = $index) {
          <button
            type="button"
            (click)="selectTab(i)"
            [class]="getTabClass(i)"
            [attr.aria-current]="selectedIndex === i ? 'page' : null"
          >
            {{ tab.label }}
          </button>
        }
      </nav>
    </div>
    <div class="mt-4">
      <ng-content />
    </div>
  `,
})
export class TabsComponent implements AfterContentInit {
  @Input() selectedIndex = 0;
  @Output() selectedIndexChange = new EventEmitter<number>();

  @ContentChildren(TabComponent) tabs!: QueryList<TabComponent>;

  ngAfterContentInit(): void {
    this.updateTabVisibility();
  }

  selectTab(index: number): void {
    this.selectedIndex = index;
    this.selectedIndexChange.emit(index);
    this.updateTabVisibility();
  }

  private updateTabVisibility(): void {
    if (this.tabs) {
      this.tabs.forEach((tab, i) => {
        tab.active = i === this.selectedIndex;
      });
    }
  }

  getTabClass(index: number): string {
    const base = 'px-4 py-2 font-medium text-sm transition-colors duration-200 border-b-2';
    if (index === this.selectedIndex) {
      return `${base} border-primary-500 text-primary-600`;
    }
    return `${base} border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300`;
  }
}

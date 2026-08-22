import { Component, Input } from '@angular/core';

/**
 * Color-coded user role badge. Used in user management, audit log, etc.
 */
@Component({
  selector: 'app-role-badge',
  standalone: true,
  template: `<span class="badge" [class]="colorClass()">{{ role }}</span>`,
})
export class RoleBadgeComponent {
  @Input({ required: true }) role!: string;

  colorClass(): string {
    const roleColors: Record<string, string> = {
      admin: 'bg-violet-600 text-white',
      compliance_officer: 'bg-blue-600 text-white',
      issuer: 'bg-teal-600 text-white',
      investor: 'bg-slate-500 text-white',
    };
    return roleColors[this.role?.toLowerCase()] ?? 'bg-slate-500 text-white';
  }
}

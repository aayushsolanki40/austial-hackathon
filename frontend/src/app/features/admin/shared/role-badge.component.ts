import { Component, Input } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';

/**
 * Color-coded user role badge. Used in user management, audit log, etc.
 */
@Component({
  selector: 'app-role-badge',
  standalone: true,
  imports: [MatChipsModule],
  template: `<mat-chip [class]="'role-chip role-chip--' + role.toLowerCase()">{{ role }}</mat-chip>`,
  styles: [
    `
      .role-chip {
        font-weight: 500;
        font-size: 0.75rem;
      }

      .role-chip--admin {
        background-color: #7c4dff;
        color: white;
      }

      .role-chip--compliance_officer {
        background-color: #2979ff;
        color: white;
      }

      .role-chip--issuer {
        background-color: #00bfa5;
        color: white;
      }

      .role-chip--investor {
        background-color: #757575;
        color: white;
      }
    `,
  ],
})
export class RoleBadgeComponent {
  @Input({ required: true }) role!: string;
}

# Swadely Frontend Design System

This document describes the Tailwind CSS-based design system for the Swadely frontend application.

## Color Palette

### Primary (Emerald/Teal - Trust & Growth)
- `primary-50` to `primary-950`: Emerald green shades
- Main usage: Primary actions, success states, navigation highlights
- Represents: Financial growth, trust, security

### Secondary (Indigo - Authority)
- `secondary-50` to `secondary-950`: Indigo blue shades
- Main usage: Secondary actions, complementary UI elements
- Represents: Authority, professionalism, stability

### Accent (Amber - Attention)
- `accent-50` to `accent-950`: Amber/gold shades
- Main usage: Warnings, highlights, important notifications
- Represents: Premium features, attention-required items

### Semantic Colors
- **Success**: Green (`green-500`, `green-600`)
- **Warning**: Orange (`orange-500`, `orange-600`)
- **Error**: Red (`red-500`, `red-600`)
- **Info**: Blue (`blue-500`, `blue-600`)
- **Neutral**: Slate shades for text, borders, backgrounds

## Typography

### Font Family
- Primary: `Inter`, `Roboto`, `Helvetica Neue`, sans-serif
- Set in `tailwind.config.js` and applied globally

### Text Scales
- `text-4xl`: Page titles (h1)
- `text-3xl`: Section headings (h2)
- `text-2xl`: Subsection headings (h3)
- `text-xl`: Card titles, prominent text
- `text-lg`: Lead paragraphs, important descriptions
- `text-base`: Body text
- `text-sm`: Secondary text, labels
- `text-xs`: Metadata, captions

### Font Weights
- `font-bold`: Headings, primary CTAs
- `font-semibold`: Subheadings, labels, emphasis
- `font-medium`: Navigation items, secondary CTAs
- `font-normal`: Body text

## Component Classes

### Cards
```scss
.card                // Standard card with shadow
.card-compact        // Smaller padding, lighter shadow
.card-glass          // Glassmorphism effect with backdrop blur
```

### Buttons
```scss
.btn-primary         // Gradient primary button with hover scale
.btn-secondary       // Gradient secondary button
.btn-outline         // Outlined button with hover fill
.btn-ghost           // Text-only button with hover background
```

### Form Elements
```scss
.form-group          // Form field container with spacing
.form-label          // Consistent label styling
.form-input          // Input field with focus ring
.form-input-error    // Error state for inputs
.form-error          // Error message text
```

### Badges
```scss
.badge               // Base badge styling
.badge-success       // Green badge for success/active states
.badge-warning       // Amber badge for warning states
.badge-error         // Red badge for error/critical states
.badge-info          // Blue badge for informational states
```

### Tables
```scss
.table-container     // Wrapper with overflow and rounded corners
.table               // Base table styling
.table thead         // Header with gradient background
.table th            // Header cells with uppercase text
.table td            // Data cells
.table tbody tr      // Row hover effects
```

### Loading Indicators
```scss
.spinner             // Animated loading spinner
```

### Status Indicators
```scss
.status-dot          // Small circular status indicator
.status-dot-success  // Green dot
.status-dot-warning  // Amber dot
.status-dot-error    // Red dot
.status-dot-info     // Blue dot
```

## Animations

### Built-in Animations
- `animate-fade-in`: Fade in effect (0.3s)
- `animate-slide-up`: Slide up with fade (0.3s)
- `animate-scale-in`: Scale in with fade (0.2s)

### Usage
Apply animation classes to page sections for smooth entry:
```html
<section class="animate-fade-in">...</section>
<div class="animate-slide-up">...</div>
```

## Layout Patterns

### Page Container
```html
<section class="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
  <div class="max-w-7xl mx-auto">
    <!-- Content -->
  </div>
</section>
```

### Responsive Grids
```html
<!-- 1-2-3 column responsive grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <!-- Cards -->
</div>
```

### Flexbox Utilities
```html
<!-- Horizontal flex with gap -->
<div class="flex items-center gap-4">...</div>

<!-- Vertical flex with spacing -->
<div class="flex flex-col space-y-4">...</div>
```

## Screen-Specific Design Patterns

### Auth Screens (Login/Register)
- Split-screen on desktop (can expand to include brand illustration)
- Full-screen gradient background
- Centered card with shadow
- Floating label inputs with focus rings
- Gradient CTA buttons

### Dashboard (Marketplace, Portfolio)
- Full-width page with max-width container
- Grid layout for cards/listings
- Filter section in card above content
- Responsive breakpoints: 1/2/3 columns

### Wallet
- Hero section with gradient balance display
- Card-based sections for funding and history
- Highlighted wire instruction details in nested grid
- Transaction table with color-coded entry types

### Admin Panel
- Dark sidebar navigation (slate-900 to slate-800 gradient)
- Active link with primary-600 background
- White content area with slate-50 background
- KPI cards with gradient backgrounds
- Data tables with sticky headers and hover effects

### KYC Onboarding
- Centered stepper with mat-stepper (Material)
- Card wrapper around stepper
- Gradient background for visual interest
- Progress indicator via Material stepper component

## Responsive Design

### Breakpoints (Tailwind defaults)
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

### Mobile-First Approach
All utility classes apply to mobile by default. Use breakpoint prefixes for larger screens:
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  <!-- Mobile: 1 col, Tablet: 2 cols, Desktop: 3 cols -->
</div>
```

## Material Components Retained

For complex interactions, Angular Material components are kept:
- `mat-dialog`: Modal dialogs
- `mat-datepicker`: Date selection
- `mat-table`: Data tables (alternative to custom HTML tables)
- `mat-snackbar`: Toast notifications
- `mat-stepper`: Multi-step forms (KYC)
- `mat-sidenav`: Admin navigation sidebar
- `mat-icon`: Icon display

These are styled via Tailwind utility classes in the template where possible.

## Implementation Notes

1. All component-specific SCSS files cleared — styles now live in:
   - Global `styles.scss` for Tailwind base/components/utilities
   - Inline Tailwind classes in component templates

2. Design system classes defined in `@layer components` in `styles.scss` for reusability

3. Color palette extended in `tailwind.config.js` for primary/secondary/accent scales

4. Custom animations defined in `tailwind.config.js` under `theme.extend.animation`

5. All existing functionality preserved — no API changes, same routes, same business logic

## Future Enhancements

- Add dark mode support via Tailwind's dark mode classes
- Expand animation library for more sophisticated transitions
- Consider custom focus-visible styles for better accessibility
- Add print styles for compliance reports
- Implement skeleton loaders for better loading UX

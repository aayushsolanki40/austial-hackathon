# Austial Logo Assets

This directory contains the official Austial brand logo files used throughout the frontend application.

## Logo Files

### austial-logo.svg
- **Type**: Horizontal logo with text
- **Usage**: Main branding, headers, login/register pages
- **Dimensions**: 240x60px viewBox
- **Features**: Letter "A" icon with gradient emerald background + "Austial" text
- **Primary color**: #10b981 (emerald-500)

### austial-icon.svg
- **Type**: Square icon/mark
- **Usage**: Sidebar branding, loading states, favicons
- **Dimensions**: 100x100px viewBox
- **Features**: Letter "A" in white on emerald background with rounded corners
- **Primary color**: #10b981 (emerald-500)

### favicon.svg
- **Type**: Favicon-optimized icon
- **Usage**: Browser favicon, PWA icons
- **Dimensions**: 32x32px viewBox
- **Features**: Simplified "A" icon for small sizes
- **Primary color**: #10b981 (emerald-500)

## Usage Examples

### In HTML Templates
```html
<!-- Full logo (horizontal) -->
<img src="assets/images/logo/austial-logo.svg" 
     alt="Austial" 
     class="h-16">

<!-- Icon/mark (square) -->
<img src="assets/images/logo/austial-icon.svg" 
     alt="Austial" 
     class="h-12">

<!-- Loading state -->
<img src="assets/images/logo/austial-icon.svg" 
     alt="Loading" 
     class="h-8 animate-pulse">
```

### In index.html
```html
<link rel="icon" type="image/x-icon" href="favicon.ico">
<link rel="icon" type="image/svg+xml" href="assets/images/logo/favicon.svg">
```

## Current Integration Points

- **Login/Register pages**: Full logo (austial-logo.svg)
- **Admin sidebar**: Square icon (austial-icon.svg)
- **Browser favicon**: Optimized icon (favicon.svg)
- **Loading states**: Animated icon throughout the app
  - Marketplace listings
  - Wallet balance and transaction history
  - Portfolio holdings and distributions
  - Admin dashboard states

## Design Notes

- All logos use the primary emerald color (#10b981) from the Austial design system
- The "A" icon design features a stylized letter with a cutout triangle, creating depth
- SVG format ensures crisp rendering at any size
- The design is simple and modern, reflecting fintech professionalism
- White space and clean lines align with the overall UI aesthetic

## Future Enhancements

Consider creating:
- Dark mode variants (white/light logo versions)
- Animated logo for splash screens
- Multiple color variants for different contexts
- PNG/WebP fallbacks for older browsers (if needed)
- OpenGraph images for social sharing

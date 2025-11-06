# March Madness Theme Consistency Improvements

## Summary
Implemented a comprehensive design system to ensure consistent theming across the entire website.

## Changes Made

### 1. CSS Design System (`static/style.css`)
Created centralized CSS variables for:
- **Colors**: Primary (#0033A0 blue), Accent (#FF6600 orange), semantic colors (success, warning, danger, info)
- **Typography**: Font families, sizes (xs to 4xl), and weights
- **Spacing**: Consistent spacing scale (xs to 3xl)
- **Border Radius**: Standardized corner radii (sm to full)
- **Shadows**: Elevation system (xs to xl)
- **Transitions**: Smooth, base, and fast transitions
- **Z-index**: Layered z-index system

### 2. Removed Inline Styles
- Moved 850+ lines of inline CSS from `templates/index.html` to external stylesheet
- Replaced inline `style=""` attributes with CSS classes
- Added `.table-view` class to body for scoped styling

### 3. Standardized Buttons
- Created consistent button styles (.btn-primary-custom, .btn-secondary-custom)
- Unified hover states and transitions
- Added size variants (.btn-sm-custom)

### 4. Updated Bracket Page
- Converted hardcoded colors to CSS variables
- Updated matchup cards, seeds, scores, and ticker styles
- Maintained dark/light mode compatibility

### 5. Color Consolidation
**Before**: 33+ distinct hardcoded hex colors
**After**: Centralized color system with semantic naming

## Benefits
1. **Maintainability**: Single source of truth for design tokens
2. **Consistency**: All buttons, colors, and spacing now uniform
3. **Performance**: Reduced inline styles improve rendering
4. **Scalability**: Easy to update theme globally
5. **Accessibility**: Consistent font sizes and color contrast

## March Madness Theme
- **Primary Blue**: #0033A0 (brand color for headers, links)
- **Accent Orange**: #FF6600 (CTAs, highlights, leader indicators)
- **Supporting Colors**: Maintained existing success/warning/danger semantics
- **Typography**: Inter font family for modern, clean appearance

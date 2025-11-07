# March Madness Theme Consistency

## Design System Implemented

### CSS Variables (`:root` in style.css)

**Brand Colors:**
- `--color-primary`: #0033A0 (Primary Blue - for headers, nav, primary elements)
- `--color-accent`: #FF6600 (Orange - for CTAs, highlights, upset indicators)

**Usage Guide:**
- Use `var(--color-primary)` instead of hardcoded #0033A0
- Use `var(--color-accent)` instead of hardcoded #FF6600
- Use `var(--color-info-light)` for bracket blues (#3b82f6)

### Color Consistency Rules

1. **Primary Actions**: Orange accent color (`--color-accent`)
   - Apply filters button
   - Year badges
   - Upset indicators
   - Leader highlights

2. **Headers & Navigation**: Primary blue (`--color-primary`)
   - Navigation bar border
   - Page titles
   - Section headers (can use gradients with primary-light)

3. **Brackets & Stats**: Info blue (`--color-info-light`)
   - Region names
   - Seed badges
   - Scores
   - Borders and highlights

### Current Status

✅ **Completed:**
- CSS design system variables added
- Key bracket page colors updated to use variables
- Foundation for consistent theming established

📋 **Remaining Work:**
- Move 830+ lines of inline CSS from index.html to style.css
- Replace remaining hardcoded colors throughout codebase
- Standardize button styles across all pages
- Create utility classes for common patterns

### Quick Reference

**Before:**
```css
color: #0033A0;  /* Hardcoded */
background: #FF6600;  /* Hardcoded */
```

**After:**
```css
color: var(--color-primary);  /* Design system */
background: var(--color-accent);  /* Design system */
```

This ensures all instances of the brand colors update together if the design ever changes.

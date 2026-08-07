# Palette's Journal - Critical Learnings

## 2025-02-14 - Accessibility and Focus Indicators for Sidebar Navigation
**Learning:** Screen readers and keyboard navigators require robust landmark semantics and visible focus indicators when moving through core navigation elements like sidebars. Missing ARIA labels or default/hidden outlines on active/unfocused navigation links prevent users with assistive technologies from identifying the structural parts of the layout, and hide currently focused items under keyboard navigation.
**Action:** Use landmarks like `aria-label="Barra lateral"` and `aria-label="Navegação Principal"` to designate sidebar structure. Apply standard, highly visible `focus-visible` rings with offset rings tailored to the background theme (e.g. `focus-visible:ring-white/40 focus-visible:ring-offset-primary`) to ensure smooth visual tracking, and utilize `aria-current="page"` to programmatically announce active routes.

# Palette's Journal

## 2025-06-15 - Improving Landmark and Navigation Accessibility in NextJS/React Sidebars
**Learning:** Decorative icons rendered inside standard text-bearing anchor/link elements without an explicit `aria-hidden="true"` attribute can be redundantly announced or misread by screen readers as raw graphic code. Furthermore, custom sidebar navigations should always contain defined ARIA landmark roles or distinct labels to allow blind and visually impaired users to use standard navigation rotor features to orient themselves on first load.
**Action:** Always wrap sidebars in `<aside>` elements with an explicit `aria-label` defining the layout landmark. Label `<nav>` items to distinguish main navigation from other nav areas, specify `aria-current="page"` on current active path anchors, and declare `aria-hidden="true"` on decorative inline elements like Lucide or custom icons.

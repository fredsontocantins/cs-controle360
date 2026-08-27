## 2025-05-18 - Sidebar Accessible Landmarks and Focus States
**Learning:** Next.js sidebar navigation components require explicit `aria-label` attributes on `<aside>` and `<nav>` elements, `aria-current="page"` on active route links, and `focus-visible:ring-2` styles to ensure full keyboard and screen reader accessibility.
**Action:** When building or modifying navigation components, always include accessible landmarks, mark current page links with `aria-current`, hide decorative icons with `aria-hidden="true"`, and provide visible keyboard focus rings.

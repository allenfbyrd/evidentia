# shadcn/ui components

These files are the standard shadcn/ui "new-york" preset components, copy-pasted into the repo per the shadcn convention (rather than installed as a package). The goal is that upgrading shadcn/ui is a deliberate act of re-copying with review, not an implicit npm update.

v0.4.0-alpha.1 ships the minimal set used by the pages that landed in alpha.1:

- `button.tsx`
- `card.tsx`
- `badge.tsx` (with Evidentia severity variants)
- `separator.tsx`

v0.4.0-alpha.2 will add: `dialog.tsx`, `select.tsx`, `tabs.tsx`, `toast.tsx`, `input.tsx`, `label.tsx`, `switch.tsx`, `form.tsx` (react-hook-form integration).

Accessibility: Radix primitives (shadcn's foundation) give us WCAG 2.1 AA compliance out of the box for keyboard nav, ARIA labels, and focus management. Verify with `npm run test` + `axe` when that tool is wired in alpha.2.

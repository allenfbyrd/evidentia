# @evidentia/ui

React + Vite + TypeScript + shadcn/ui frontend for **Evidentia**. Served by the `evidentia-api` FastAPI backend.

> **Note:** This is a Node/Vite project colocated in the Evidentia monorepo. It is **not** a Python workspace member — `uv` does not touch this directory. End users never build the frontend themselves; built assets are bundled inside the `evidentia-api` wheel at release time.

## Stack

- **React 18** + **TypeScript** (strict mode)
- **Vite 5** — dev server + production bundler
- **shadcn/ui** — Radix primitives styled with Tailwind CSS (WCAG 2.1 AA friendly)
- **TanStack Query v5** — API cache + mutations
- **TanStack Table v8** + **TanStack Virtual** — 200–1000-row gap tables
- **React Router 6** — SPA routing
- **Zustand** — onboarding wizard state
- **React Hook Form** + **Zod** — form validation
- **Recharts** — severity donut, framework coverage charts
- **Vitest** + **React Testing Library** — unit + component tests
- **Playwright** — E2E smoke tests against `evidentia serve`

## Development

Requires Node 20+ and npm (or pnpm/yarn if you prefer — `package-lock.json` is checked in).

```bash
# Install deps
npm install

# Terminal 1 — Vite dev server at http://127.0.0.1:5173
npm run dev

# Terminal 2 — FastAPI backend with CORS for Vite at http://127.0.0.1:8000
cd ../..   # to repo root
uv sync --all-packages
evidentia serve --dev   # wires permissive CORS for :5173
```

Vite proxies `/api/*` to the FastAPI server, so `fetch("/api/health")` from the UI just works.

## Build

```bash
npm run build
```

Produces `dist/` — static HTML + hashed JS/CSS assets. At release time the GitHub Actions workflow copies `dist/*` into `packages/evidentia-api/src/evidentia_api/static/` so the Python wheel ships self-contained.

## Test

```bash
npm run typecheck         # TypeScript strict
npm run test              # Vitest watch
npm run test:coverage     # Vitest with v8 coverage
npm run e2e               # Playwright E2E (requires `evidentia serve` in another terminal)
```

## Accessibility

shadcn/ui is built on Radix UI primitives, which give us WCAG 2.1 AA compliance out of the box for most widgets. Remaining work per component is tracked in `docs/gui/a11y.md`.

## Layout

```
packages/evidentia-ui/
├── package.json
├── vite.config.ts            # + test + build config
├── tailwind.config.ts
├── tsconfig.json / tsconfig.node.json
├── components.json           # shadcn/ui config
├── index.html
└── src/
    ├── main.tsx              # QueryClient + Router + StrictMode
    ├── App.tsx               # route tree
    ├── index.css             # Tailwind + shadcn CSS vars
    ├── components/
    │   ├── layout/           # AppLayout, Header, Sidebar
    │   ├── ui/               # shadcn/ui primitives (Button, Dialog, etc.)
    │   └── gap/              # gap-analysis-specific composites
    ├── routes/               # one file per page
    ├── hooks/                # TanStack Query hooks
    ├── lib/
    │   ├── api.ts            # typed fetch wrapper
    │   └── utils.ts          # cn() + helpers
    └── types/
        └── api.ts            # TS mirrors of Python Pydantic models
```

## License

Apache-2.0 — see [`LICENSE`](../../LICENSE).

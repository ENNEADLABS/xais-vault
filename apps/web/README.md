# XAIS Vault — Frontend

Next.js 16 frontend for XAIS Vault. App Router, TypeScript, Tailwind CSS v4, shadcn/ui.

## Stack

| | |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 + shadcn/ui |
| State | TanStack React Query + Zustand |
| i18n | next-intl (fr / en) |
| Auth | Supabase Auth (@supabase/ssr) |
| Realtime | Supabase Realtime |

## Dev

```bash
npm ci
npm run dev        # http://localhost:3000
npm run build      # production build
npx tsc --noEmit   # type check
npx vitest run     # tests
```

## Structure

```
src/
├── app/
│   ├── [locale]/
│   │   ├── (auth)/       # login, signup, callback
│   │   └── (app)/        # dashboard, workspaces/[id], settings, onboarding
│   └── layout.tsx
├── components/
│   ├── ui/               # shadcn primitives
│   ├── layout/           # ThreePanelLayout, Sidebar, Header
│   ├── workspace/        # Sources, Chat, Insights, Notes, Deliverables
│   ├── workspaces/       # WorkspaceCard, WorkspaceToolbar, EmptyState
│   └── settings/         # OrgSettings, ApiKeys, Webhooks
├── lib/
│   ├── api.ts            # typed fetch client
│   ├── supabase/         # auth client
│   ├── hooks/            # TanStack Query hooks
│   └── i18n/             # messages en/fr
├── stores/               # Zustand UI stores
└── types/                # TypeScript types
```

## Environment

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

See [../../docs/environment.md](../../docs/environment.md) for the full list.

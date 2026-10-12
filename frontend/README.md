# Threadit — Frontend

React + TypeScript (Vite) SPA for the Threadit message board. Single sober theme, highly configurable.

## Switch backend target

The app is backend-agnostic — pick a target by copying one env preset to `.env.local`:

```bash
# Local services + Floci (dev auth, no Cognito):
cp .env.local-floci.example .env.local

# Real AWS (ALB API + real Cognito sign-in):
cp .env.aws .env.local        # .env.aws holds the real ALB/Cognito values (gitignored)
```

`.env.local` is gitignored. The two `.example` files are committed templates; the real
`.env.aws` (with live ALB DNS + Cognito IDs from `terraform output`) stays local.

- **Floci/local**: `VITE_DEV_USER_ID` set → auth stubbed, writes use `x-user-id`, reads/writes split across `:8080`/`:8081`.
- **AWS**: no dev user → real Cognito OIDC sign-in; one `VITE_API_BASE_URL` (ALB routes read/write by method).

## Plug in and run

Everything a new deployer edits lives in two files + env:
- **`.env.local`** — endpoints + Cognito (copy from `.env.example`): API base URL, Cognito region / user-pool ID / client ID / domain, redirect URI. (6 values.)
- **`src/brand.ts`** — all design tokens (typography, color, spacing, logo). Edit to rebrand the whole app.
- **`src/config.ts`** — reads env; feature flags (`search`, `images`).

No component code needs editing to point at a new backend or rebrand.

```bash
npm install
cp .env.example .env.local   # fill in the 6 values
npm run dev                  # http://localhost:5173
npm run typecheck            # tsc --noEmit
npm run build                # production build
```

## Structure
```
src/
  config.ts         # runtime config (env) — plug-in point
  brand.ts          # design tokens — single source of truth
  theme.ts          # tokens -> CSS variables (single theme)
  lib/
    api/            # typed client + DTOs matching /v1 OpenAPI
    auth/           # Cognito OIDC (PKCE), in-memory token, AuthProvider
    hooks.ts        # TanStack Query hooks
    errors.ts       # RFC 9457 -> user messages
  components/       # Logo, PostList, CommentTree, Composer, SearchBar, ui primitives
  pages/            # Home, PostDetail, Create, Search, AuthCallback, Layout
```

## Notes
- Reads are public; writes require sign-in (Cognito). Access token kept in memory only.
- Comments render as a threaded tree (depth cap 8). Cursor "load more", not numbered pages.
- Search is eventually consistent (just-posted content may lag a few seconds).

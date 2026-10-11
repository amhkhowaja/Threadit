# Threadit — Frontend Build Prompt

> **Status:** Complete, implementation-ready frontend build prompt. Hand this entire
> document to the frontend implementer. It has two parts:
>
> - **Part 1 — UX Architecture** (flows, IA, page specs, state catalog, accessibility,
>   error→UX mapping, visual direction, brand concept). *What the experience is and why.*
> - **Part 2 — UI Architecture** (stack, project structure, the configuration layer,
>   final design tokens, typography system, concrete logo/SVG, component system with
>   props + API bindings, state/data-fetching with TanStack Query, the typed API client,
>   auth/token handling, performance budget, testing). *How it is built.*
>
> **Read both parts before writing any code.** Part 2 implements the flows, states,
> vocabulary, and accessibility contract defined in Part 1 — it does not override them.
>
> **Stack (fixed):** React + TypeScript + Vite + React Router + TanStack Query. Single
> theme (NO dark/light toggle). Minimalistic, sober, content-first.
>
> **Prime directive — configuration-driven:** A new deployer edits only two files —
> `src/config.ts` (endpoints, Cognito, feature flags; fed by env) and `src/brand.ts`
> (all design tokens, typography, logo) — plus a `.env`. **Plug in 6 values + brand =
> running app, zero component changes.** See §2.17 "Getting Started" for the exact 6.
>
> **Do not invent backend behavior.** Use only the `/v1` endpoints and DTOs specified in
> Part 1 §0–§2 and summarized in Part 2 §2.10. No votes, profiles, edit/delete, or
> comment images — none exist in the contract.

---

> ⬇️ **PART 1 — UX ARCHITECTURE** ⬇️

---

## 0. Requirement Summary, Users & Assumptions

### What Threadit is
A Reddit-like **threaded message board**. Anyone can read everything without an
account. Writing (posting, replying, attaching images) requires signing in via Amazon
Cognito. Discussion is organized as **posts**, each with a **tree of comments** nested
up to 8 levels deep.

### Users & jobs-to-be-done
- **Lurker (signed-out, majority traffic):** browse latest posts, read a post and its
  full comment tree, search by keyword, follow a shared deep link. Never blocked from
  reading.
- **Contributor (signed-in):** create a post (optionally with one image), reply to a
  post or to any comment, search for prior discussion before posting.
- **Returning author:** check that a just-created post/comment actually landed
  (read-your-own-write), find their own posts (`user_id` filter).

### Success metrics for the experience
- Time-to-first-readable-content on Home and Post detail is minimal (content-first,
  skeletons).
- Write-action-to-confirmed-visible is perceived as instant (optimistic UI +
  read-your-own-write).
- Zero dead ends: every error state offers a next action.
- A signed-out user never hits a wall they can't understand; write gates always
  explain *why* and offer sign-in.

### Assumptions (stated, since the contract doesn't specify)
1. **`userId` is an opaque Cognito subject (UUID-like), not a human display name.** The
   contract returns `userId` only — there is no username/profile endpoint. **The UI
   renders a short, stable, de-identified handle derived from `userId`** (e.g.
   `user-3f9a`) plus a deterministic avatar glyph. We do **not** invent a profile page
   or claim a real name. *(Open question for API Architect: is there a display-name or
   profile lookup? If yes, we'll swap the derived handle for it.)*
2. **No vote/score/sort-by-popularity exists in the contract.** Ordering is
   backend-defined (list returns thread/recency order). The UI does **not** show
   upvotes, karma, or a "hot/top/new" switcher beyond what `last=5|10|20` and
   `search_keyword`/`user_id` filters provide. We will not fabricate ranking UI.
3. **No edit/delete endpoints exist.** The UI shows no edit/delete affordances on
   posts or comments. (If added later, they slot into the existing action row.)
4. **One image per post.** `attachments:presign` is scoped to a post; the create-post
   flow supports a single image attachment. Comments have no attachment endpoint, so
   **no image attach on comments.**
5. **`last=5|10|20`** is treated as a "recency window" quick filter (how many of the
   most-recent posts to pull), mutually consistent with cursor paging; see Home spec.
6. Multi-tenancy is **N/A** at the data level — there is no tenant key in the contract.
   The only "tenant-like" dimension is per-deployment branding via config. No
   cross-tenant isolation concerns in the UI.

---

## 1. Information Architecture & Navigation Map

### Conceptual vocabulary (use consistently everywhere)
- **Post** — a top-level thread (title + body + optional image).
- **Comment / Reply** — a node in a post's comment tree. "Reply" is the verb; "comment"
  is the noun. A reply to the post is a **top-level comment** (`parentId = null`).
- **Thread** — the post plus its comment tree.
- **Continue thread** — the affordance shown when nesting hits depth 8.
- **Load more** — cursor-based incremental fetch (never "page 2").

### Route map (deep-linkable, back-navigable)

```
/                          Home — latest posts (default list)
/search?q=<keyword>        Search results (search_keyword)
/u/:userId                 Posts by a specific user (user_id filter) [read-only view]
/posts/:postId             Post detail + threaded comments
/posts/:postId#c-:commentId  Deep link to a specific comment (scroll + highlight)
/new                       Create post (auth-gated; redirects to sign-in if signed out)
/signin                    Sign in (Cognito hosted/OIDC entry)
/signup                    Sign up (Cognito)
/auth/callback             OIDC redirect handler (exchange code, then return to origin)
*                          Not found (404) — within-app, offers Home + Search
```

**Routing rules**
- Every list/detail view is a **real URL** and shareable. Browser back/forward restores
  scroll position and loaded list state where feasible (list "load more" state is
  restored from cache; see Part 2 data-fetching).
- `user_id` and `search_keyword` are **URL-driven** (query/path), so filters survive
  refresh and sharing.
- Auth-gated routes (`/new`) check session on entry; if signed out, route to `/signin`
  with a `returnTo` so the user lands back where they intended after auth.
- `last=5|10|20` is a query param on Home (`/?last=10`), so a chosen recency window is
  shareable and restored on back.

### Navigation chrome (persistent across pages)

**Top bar (single row, calm, content-first):**
```
[ Threadit logo ]        [ Search field                    ]        [ New post ] [ Account ]
```
- **Logo** → Home. Always present, top-left, keyboard-focusable, `aria-label="Threadit — home"`.
- **Search field** → submits to `/search?q=`. Present on every page (search is a
  primary job). On mobile it collapses to a search icon that expands.
- **New post** → `/new`. Visible to everyone; if signed out, clicking it opens the
  sign-in prompt (does not hide the button — hiding write affordances from lurkers
  creates confusion; we show + gate instead).
- **Account** → when signed out: "Sign in" link. When signed in: a menu with the
  derived handle, "My posts" (`/u/:myUserId`), and "Sign out".

**No sidebar, no secondary nav, no footer clutter.** The board is the content. A single
top bar + the main column is the whole chrome. This is deliberate: minimalist, sober,
and keeps the reading column dominant.

### Navigation guarantees (E2E — no orphans)
- From **Home** → any post → back to Home (state preserved).
- From a **Post** → each comment's author handle → that user's posts (`/u/:userId`).
- From **Search** → a result → post detail → back to the same search results.
- From **Create post** success → the new post's detail page.
- From any **error/empty/404** → at minimum a link Home and the Search field.
- **Sign-in** is reachable from every write gate and from the top bar.

---

## 2. Page-by-Page UX Specification

Each page lists: purpose, API binding, layout (text wireframe), and the full **state
catalog** (loading / empty / error / partial / permission). States are first-class, not
afterthoughts.

---

### 2.1 Home / Post List

**Purpose:** The entry point. Browse the most recent posts; narrow by recency window;
jump into a thread; start a new post.

**API binding:** `GET /v1/posts?limit=&cursor=&last=&user_id=`
Returns `PageResponse { items: [PostResponse], nextCursor, limit }`.
Pagination is **cursor-based "load more"**, never numbered pages.

**Text wireframe**
```
┌───────────────────────────────────────────────────────────┐
│ [Threadit]        [ Search… ]            [New post] [Account]│
├───────────────────────────────────────────────────────────┤
│  Latest                              Show: ( 5 ) (10) (20)  │  ← recency window (last=)
│                                                             │
│  ┌───────────────────────────────────────────────────────┐│
│  │ Post title (truncates to ~2 lines)                     ││
│  │ by user-3f9a · 2h ago                                  ││
│  │ First ~160 chars of body as a muted preview…           ││
│  │ 🖼 image indicator (only if post has an attachment)     ││
│  └───────────────────────────────────────────────────────┘│
│  ┌───────────────────────────────────────────────────────┐│
│  │ … more post cards …                                    ││
│  └───────────────────────────────────────────────────────┘│
│                                                             │
│                 [ Load more ]  (hidden when no nextCursor)  │
└───────────────────────────────────────────────────────────┘
```

**Interaction**
- Whole card is a single click/tap target → `/posts/:postId`. The author handle is a
  nested, separately-focusable link → `/u/:userId`. (Nested interactive elements must
  be real links, not click handlers on a div, for keyboard + screen-reader correctness.)
- **"Show: 5 / 10 / 20"** sets the `last` recency window. Treat as a segmented control.
  Changing it refetches from the top (new list, resets cursor) and updates the URL
  (`/?last=10`). Default = 10. Rationale: a calm default; power users widen it.
- **Load more**: appends `items` using `nextCursor`. The button shows an inline spinner
  while fetching and is disabled during the request (prevents double-fetch). When
  `nextCursor` is absent/null, replace the button with a quiet end-of-list marker
  ("You're all caught up.").
- **Timestamps** render relative ("2h ago") with the absolute time in a `title`/tooltip
  and a `<time datetime>` for machines.

**State catalog**
- **Loading (initial):** 5–6 **skeleton cards** matching card geometry (title bar, meta
  line, two preview lines). No spinner-only screens — skeletons preserve layout and
  reduce perceived wait.
- **Loading (load-more):** keep existing cards; spinner inside the "Load more" button.
- **Empty (no posts at all):** calm centered state — "No posts yet." + primary action
  "Write the first post" (→ `/new`, gated). Not an error tone.
- **Empty via filter (`/u/:userId` has none):** "This user hasn't posted yet." + link
  back to Home.
- **Error (network / 5xx on list):** inline, non-destructive — "Couldn't load posts."
  with a **Retry** button and the `correlationId` shown small for support. Previously
  loaded cards (on a load-more failure) stay visible; only the load-more control shows
  the error + retry.
- **429 on list read:** "You're browsing quickly — give it a second." Auto-enable retry
  after `Retry-After`; show a countdown on the Retry button.

---

### 2.2 Post Detail + Threaded Comments

**Purpose:** Read a full thread: the post, then its comment tree; reply at any depth;
load deep subtrees lazily.

**API binding:**
- Post: `GET /v1/posts/{post_id}` → `PostResponse {id,title,body,userId,createdAt,updatedAt}`.
  Use `?consistent=true` for the read-your-own-write case (see §3).
- Comments: `GET /v1/posts/{post_id}/comments?limit=&cursor=&rootCommentId=`
  → `PageResponse { items: [CommentResponse] }`. `CommentResponse { id, postId, userId,
  text, depth, parentId, rootCommentId, createdAt }`. Items arrive **in thread order**
  (materialized path). **Depth cap = 8.**

**Text wireframe**
```
┌───────────────────────────────────────────────────────────┐
│ [Threadit]        [ Search… ]            [New post] [Account]│
├───────────────────────────────────────────────────────────┤
│  ‹ Back to posts                                            │
│                                                             │
│  POST TITLE  (large, strong)                                │
│  by user-3f9a · 3h ago · edited? (only if updatedAt>createdAt)│
│                                                             │
│  Body text, full, readable measure (~65–75ch column).       │
│  [ optional image, max-width within column, lazy-loaded ]   │
│                                                             │
│  [ Reply to post ]                                          │
│  ─────────────────────────────────────────────────────────│
│  Comments                                                   │
│                                                             │
│  ▏ user-9c2 · 2h ago                                        │  depth 0
│  ▏ comment text…                                            │
│  ▏ [Reply]                                                  │
│  ▏  ▏ user-4a1 · 1h ago                                     │  depth 1
│  ▏  ▏ reply text…                                           │
│  ▏  ▏ [Reply]                                               │
│  ▏  ▏  ▏ … (indent increases per depth, capped visually)    │
│  ▏  ▏  ▏ ↳ Continue thread →   (at depth 8)                 │  depth cap
│                                                             │
│                 [ Load more comments ]  (if nextCursor)     │
└───────────────────────────────────────────────────────────┘
```

**Threaded rendering rules**
- Comments come back pre-ordered by materialized path; the client reconstructs nesting
  using `parentId` / `depth` / `rootCommentId`. Each comment is a node with a left
  **indent + a vertical "thread line"** indicating depth. Indentation increases per
  depth but is **capped in pixels** after ~depth 5 so deep threads don't crush the
  reading column on narrow screens (indent stops growing; the thread line still marks
  nesting).
- **Collapse/expand:** each comment with children has a collapse toggle (caret) on its
  thread line. Collapsing hides the subtree and shows a count ("12 replies hidden").
  State is per-node, client-side, and preserved while on the page. This is the primary
  tool for navigating large trees.
- **Depth cap (8) → "Continue thread":** when a node is at `depth === 8` (max renderable)
  and has deeper descendants, render a **"Continue thread →"** link instead of nesting
  further. It loads that subtree as a focused view by calling
  `GET …/comments?rootCommentId=<thatCommentId>` and re-roots the display at that node
  (breadcrumb back to the full post). This matches the backend's lazy-subtree model and
  prevents unbounded horizontal nesting.
- **Lazy subtree "load more replies":** a subtree that was truncated (backend returned a
  partial branch, signaled by its own `nextCursor` within that `rootCommentId` scope)
  shows **"Load more replies"** under the branch. Fetch uses `rootCommentId` of that
  branch + `cursor`. Appends into the existing node — does not reload the whole tree.
- **Top-level "Load more comments":** paginates additional top-level branches via the
  post-level `nextCursor`.

**Reply affordances** (see §2.4 for the composer behavior)
- "Reply to post" sits directly under the post body (creates a top-level comment,
  `parentId = null`).
- Each comment has an inline **[Reply]** that opens a composer **in place, directly
  beneath that comment**, pre-scoped to `parentId = thatCommentId`. Only one inline
  composer open at a time (opening another closes/parks the previous with a guard if it
  has unsaved text — see §3 draft-guard).

**State catalog**
- **Loading post:** skeleton for title, meta, 3 body lines; comments area shows a quiet
  "Loading comments…" with 3 comment skeletons.
- **Post loads, comments still loading:** show the post immediately (staggered load) —
  reading can start before comments arrive.
- **Empty comments:** "No comments yet. Be the first to reply." + the reply composer
  entry.
- **Post 404:** full in-app Not Found for the post — "This post doesn't exist or was
  removed." + Back to Home + Search. (Do not show a broken shell.)
- **Comments error (post ok):** post stays readable; comments area shows "Couldn't load
  comments" + Retry. Partial failure must not blank the post.
- **Subtree load-more error:** inline under that branch only; Retry; rest of tree intact.
- **429 while loading:** same "slow down" + Retry-After countdown pattern as Home.

---

### 2.3 Create Post

**Purpose:** Compose and publish a new top-level post, optionally with one image.

**API binding:** `POST /v1/posts` with `CreatePostRequest { title (1..300), body
(1..40000) }`. Requires **JWT** + **Idempotency-Key** header (client UUID, one per
submit attempt). `201 → PostResponse`. **`userId` comes from the token — never a field
in the form.** Image attach is a separate presign step (§2.5) performed before/with the
create.

**Access:** auth-gated. Signed-out users who reach `/new` are routed to `/signin` with
`returnTo=/new`; after auth they land on the composer.

**Text wireframe**
```
┌───────────────────────────────────────────────────────────┐
│  ‹ Cancel                                     New post      │
│                                                             │
│  Title                                                      │
│  [ single-line input …………………………………………… ]  142/300        │
│                                                             │
│  Body                                                       │
│  [ multi-line textarea                                   ]  │
│  [                                                        ]  │
│  [                                                        ]  12,004/40,000
│                                                             │
│  Image (optional)                                           │
│  [ Add image ]  or drag a file here · PNG/JPG/WebP · ≤5MB   │
│   └ (after select) [thumbnail] filename.png · 2.1MB · [×]   │
│                                                             │
│                                   [ Cancel ]  [ Publish ]   │
└───────────────────────────────────────────────────────────┘
```

**Validation (mirror the API exactly)**
- **Title:** required, 1–300 chars. Live counter; turns warning near the limit, blocks
  at over-limit. Field-level inline message on blur/submit ("Title is required." /
  "Title must be 300 characters or fewer.").
- **Body:** required, 1–40,000 chars. Live counter. Over-limit blocks submit with inline
  message.
- **Publish** is disabled only while actively invalid *after* a first interaction — never
  silently disabled with no explanation. If disabled, a hint says why.
- Validate client-side to match the contract, but **always trust the server's 400** as
  the source of truth and surface its `detail` inline on the relevant field where
  possible.

**Submit behavior**
- Generate a fresh **Idempotency-Key (UUID v4)** per submit *attempt* and **reuse the
  same key across automatic retries** of that same attempt (so a retry after a network
  blip can't create a duplicate). A new user-initiated submit after a terminal failure
  gets a new key.
- On submit: button → "Publishing…", disabled, inline spinner. Prevent double-submit.
- On `201`: **optimistic navigation** to `/posts/:newId`. Because of read-your-own-write,
  the detail page fetches with `?consistent=true` on first load so the author
  immediately sees their post (see §3).

**State catalog**
- **Idle / editing:** counters live; image optional.
- **Submitting:** disabled form, spinner; cancel still possible before response (abort).
- **401 (token expired mid-session):** intercept, keep the draft in memory, open sign-in,
  return and **re-submit the same draft** (user doesn't lose work). Message: "Your
  session expired — sign in to publish. Your draft is saved."
- **400 validation (server):** map to fields; focus the first errored field.
- **409 idempotency conflict:** the post was already created with this key — **treat as
  success**: navigate to the created post (the server should return/point to it) rather
  than showing a scary error. Message if needed: "This post was already published."
- **429:** "You're posting quickly — try again in Ns." Keep draft; countdown on Publish.
- **5xx / network:** "Couldn't publish. Your draft is safe — try again." Retry reuses the
  same Idempotency-Key.
- **Image sub-states:** see §2.5.

---

### 2.4 Reply / Create Comment

**Purpose:** Reply to a post (top-level) or to any comment (nested), inline and in
context.

**API binding:** `POST /v1/posts/{post_id}/comments` with `CreateCommentRequest { text
(1..10000), parentId? }` (`parentId = null` → top-level). Requires **JWT** +
**Idempotency-Key**. `201 → CommentResponse`.

**Composer behavior**
- Opened inline (under the post for top-level, under the target comment for a reply).
- Shows **who you're replying to** for context ("Replying to user-9c2") so the user never
  loses the thread.
- **Text:** required, 1–10,000 chars, live counter, same over-limit blocking as post body.
- **Idempotency-Key:** one UUID per submit attempt, reused across auto-retries (as §2.3).
- Buttons: **[Cancel]** and **[Reply]**. Submitting → "Posting…", disabled, spinner.

**Optimistic insertion (read-your-own-write)**
- On submit, immediately insert a **pending comment node** at the correct position in the
  tree (nested under `parentId`, or at top level), rendered in a subtle "sending" style
  (slightly muted + a tiny "sending…" marker). The composer closes; focus moves to the
  new node so a screen reader announces it.
- On `201`: reconcile the pending node with the real `CommentResponse` (swap temp id for
  real `id`, drop "sending" style). Announce "Reply posted" politely.
- On failure: mark the pending node as **failed** in place with "Couldn't post — Retry /
  Discard" actions (do NOT silently vanish the user's text). Retry reuses the same
  Idempotency-Key. Discard removes the node and restores the text into a reopened
  composer so nothing is lost.

**Depth / 422 handling**
- Replying is allowed up to depth 8. The reply affordance on a node already at the max
  depth is replaced by **"Continue thread →"** (re-root view), not a reply box — so the
  user is guided before they can hit the cap.
- If the server still returns **422 (depth exceeded)** (race or client/display skew),
  show an actionable inline message: "This thread is at its maximum depth. Open it as its
  own thread to keep replying." with a **"Continue thread →"** action that re-roots via
  `rootCommentId` and reopens the composer there.

**State catalog**
- **Idle (closed):** just the [Reply] affordance.
- **Open / editing:** composer with context header + counter.
- **Submitting / pending:** optimistic node visible + composer closed.
- **401:** keep text, prompt sign-in, return and resubmit same draft + key.
- **409:** treat as success; reconcile to the existing comment.
- **422:** depth message + Continue-thread action (above).
- **429:** "Slow down" + Retry-After; keep text.
- **5xx/network:** failed pending node + Retry/Discard.

---

### 2.5 Image Attach (on Create Post)

**Purpose:** Attach a single image to a post via presigned direct-to-S3 upload.

**API binding (two steps):**
1. `POST /v1/posts/{post_id}/attachments:presign` with `PresignRequest { contentType,
   sizeBytes }` → `PresignResponse { url, objectKey, expiresIn }`. Requires **JWT**.
2. Client does a **direct S3 `PUT`** of the raw image bytes to `url`.
Allowed image types only; **max 5MB**.

> **Sequencing note / open question for API Architect:** presign is scoped to
> `{post_id}`, which implies the post must exist before attaching. Two viable flows:
> **(A)** create the post first (§2.3 `201` gives us the id), then presign + PUT, then the
> post shows the image on next read; or **(B)** a draft/post-first pattern. The contract
> as given supports **(A)**. **UX designs for (A):** the "Publish" action, when an image
> is staged, runs: create post → presign → S3 PUT, with a combined progress experience,
> and treats the image as best-effort (post still succeeds if the image step fails; user
> is told the image didn't attach and can retry). *If the backend expects a different
> order, flag it; UX adapts.*

**Client-side pre-checks (before any network)**
- **Type:** accept only allowed image MIME types (e.g. PNG/JPG/WebP — final allowlist
  from config). Reject others instantly with "Only image files are supported (PNG, JPG,
  WebP)."
- **Size:** reject >5MB instantly: "Image must be 5MB or smaller. This file is 7.3MB." No
  wasted upload.
- Show an immediate local **thumbnail preview** (object URL) and filename + size, with a
  **[×] remove**.

**Upload experience**
```
[thumbnail]  filename.png · 2.1MB     [progress ▓▓▓▓▓░░░ 62%]   [×]
```
- Determinate progress bar from the S3 PUT upload progress.
- On success: thumbnail stays, "Attached ✓".
- On failure (expired presign / network / S3 error): "Upload failed — Retry." Re-presign
  on retry (presign may have expired per `expiresIn`).

**State catalog**
- **No image:** the optional "Add image" affordance.
- **Selected (pre-upload):** thumbnail + metadata + remove.
- **Uploading:** progress + cancelable.
- **Uploaded:** confirmed thumbnail.
- **Rejected (type/size):** inline error, nothing uploaded, user can pick another.
- **Presign 401:** session expired → sign-in → resume.
- **Presign/PUT 5xx or expired:** "Upload failed — Retry" (re-presign).
- **Post published but image failed:** post detail opens normally with a dismissible
  notice: "Your post was published, but the image didn't attach. Add it again?" — honest,
  non-blocking.

---

### 2.6 Search Results

**Purpose:** Find posts by keyword.

**API binding:** `GET /v1/posts?search_keyword=<q>&limit=&cursor=` → same
`PageResponse`. Search hits **OpenSearch**, which is **eventually consistent (~seconds
lag)** and may **503-degrade** (search down; other reads still fine) or **501** (search
not available in this deployment).

**Text wireframe**
```
┌───────────────────────────────────────────────────────────┐
│ [Threadit]   [ keyword……………………………… ✕ ]      [New post][Acct]│
├───────────────────────────────────────────────────────────┤
│  Results for “keyword”                                      │
│  ⓘ New posts can take a few seconds to appear in search.    │  ← honest EC note
│                                                             │
│  [ result cards — same card component as Home ]             │
│                                                             │
│                 [ Load more ]  (if nextCursor)              │
└───────────────────────────────────────────────────────────┘
```

**Interaction**
- Submitting the top-bar search navigates to `/search?q=…` (URL-driven, shareable,
  back-navigable).
- Result cards are identical to Home cards (consistency).
- A persistent, low-key **eventual-consistency note** sits above results whenever a query
  is active: "New posts can take a few seconds to appear in search." This sets an honest
  expectation (the author who just posted and immediately searches may not see it yet).
- Cursor "Load more", same as Home.

**State catalog**
- **Empty query:** prompt — "Search posts by keyword." (no results list yet).
- **Loading:** skeleton cards + the EC note.
- **No matches:** "No posts match 'keyword'." + two honest hints: "Check spelling" and
  "Recently posted content may not be indexed yet — try again in a moment." + link to
  browse Home.
- **503 (search degraded):** distinct, non-alarming banner — "Search is temporarily
  unavailable. Browsing still works." + a **"Back to latest posts"** action. Do NOT show
  a generic error; be specific that *only search* is affected.
- **501 (search not available in this deployment):** hide/disable the search affordance
  for this deployment via config detection, OR if hit directly: "Search isn't available
  here." + Home. (Config can pre-disable the search box when the deployment has no search
  tier — see Part 2 config layer.)
- **429:** "Searching quickly — try again in Ns." + Retry-After countdown.
- **Network/5xx (non-search):** standard retry.

---

### 2.7 Auth Surfaces (Sign in / Sign up / Sign out)

**Purpose:** Let contributors authenticate via Amazon Cognito (OIDC). Reads are public;
writes are gated.

**API binding:** Amazon **Cognito user pool, OIDC**. The frontend uses the standard OIDC
Authorization Code + PKCE flow against Cognito (hosted UI or embedded, per Part 2 /
config). On success, the app holds a session and sends `Authorization: Bearer <JWT>` on
all writes. `userId` is derived from the token; it is **never** entered by the user.

**Model: "read freely, sign in to write."**
- Nothing in reading is gated. Only write triggers (New post, Reply, Add image, Publish)
  require a session.
- **Write-gate pattern:** when a signed-out user triggers a write, show a **sign-in prompt
  (modal or dedicated `/signin` with `returnTo`)** that:
  - Explains why: "Sign in to post and reply. Reading is always open."
  - Offers **Sign in** and **Create account**.
  - Preserves the user's intent (`returnTo`) and any in-progress draft so they resume
    exactly where they were after authenticating.

**Flows**
- **Sign in:** `/signin` → Cognito OIDC → `/auth/callback` (code exchange) → return to
  `returnTo` (or Home). Loading state during redirect/exchange.
- **Sign up:** `/signup` → Cognito sign-up (hosted) → verification per pool config → back
  to the app signed in (or to sign-in). The frontend defers field-level rules
  (password policy, email verification) to Cognito's hosted UI to avoid duplicating pool
  config; if embedded, mirror the pool's documented policy. *(Open question: hosted UI vs
  embedded forms — Part 2 / config decides; UX supports either.)*
- **Sign out:** from the Account menu → clear local session + Cognito sign-out →
  return to Home. Any open write composers close; drafts are discarded with a guard if
  non-empty.

**Session UX**
- **Token near-expiry / silent refresh:** attempt silent refresh; the user shouldn't be
  interrupted mid-read.
- **Expired session on write (401):** intercept at the write boundary, preserve draft +
  intent, prompt sign-in, resume. (Reused across §2.3/§2.4.)

**State catalog**
- **Signed out:** top bar shows "Sign in"; write affordances visible but gated.
- **Authenticating (redirect/exchange):** full-page calm "Signing you in…" with a safe
  fallback link Home if the callback errors.
- **Signed in:** Account menu with derived handle, "My posts", "Sign out".
- **Auth error / callback failure:** "We couldn't sign you in. Try again." + retry +
  Home. Never strand the user on a blank callback route.
- **403 on a write (authorized but forbidden):** "You don't have permission to do that."
  — distinct from 401; no sign-in loop.

---

## 3. Interaction & State Patterns (cross-cutting)

### 3.1 Optimistic UI + read-your-own-write
- **Create comment/reply:** optimistic insert into the tree immediately; reconcile on
  `201`; mark-failed on error (never silently drop). (§2.4)
- **Create post:** navigate optimistically to the new post; the detail page's first fetch
  uses **`?consistent=true`** so the author reliably sees their just-written post despite
  eventual consistency on normal reads. After the first consistent read, subsequent reads
  can use the normal (cheaper) path.
- **Why `consistent=true` only for the author's first view:** it's the one moment the user
  *expects* to see their own write; everywhere else, eventual consistency is acceptable
  and we don't pay the consistent-read cost.

### 3.2 Honest eventual-consistency messaging
- **Search:** always display the "new posts take a few seconds to appear" note on active
  queries (§2.6). Do not pretend search is instantly consistent.
- **No false promises:** the UI never claims a write is globally visible before it is. It
  claims only what the contract guarantees: your own write is visible to *you*
  (read-your-own-write via `consistent=true`); global/search visibility lags.

### 3.3 Cursor "Load more" (never numbered pages)
- All lists (Home, Search, user posts, comment branches) use **cursor** paging. There is
  **no page number UI**. "Load more" appends; absence of `nextCursor` ends the list with
  a quiet marker. Load-more never discards already-loaded content.

### 3.4 Threaded reply affordances
- One inline composer open at a time. Reply context header always shows the target.
- Collapse/expand per node; "Continue thread →" at depth cap re-roots via `rootCommentId`.
- "Load more replies" is scoped to a branch's `rootCommentId`; "Load more comments" is the
  post-level cursor.

### 3.5 Idempotency-Key discipline
- Generate a **UUID v4 per submit attempt**; attach as `Idempotency-Key` header on every
  write (`POST /posts`, `POST /comments`; presign per its own attempt).
- **Reuse the same key across automatic retries** of that attempt (network retry, 5xx
  retry). A fresh user-initiated submit gets a fresh key.
- Treat **409** as "already done" → reconcile to success, not an error. This makes writes
  safe under flaky networks without duplicating content.

### 3.6 Draft safety
- In-progress post bodies and reply text survive: 401 → sign-in → resume; accidental
  navigation (guard prompt if non-empty); failed submits (text preserved for retry).

### 3.7 Anti-frustration
- No rage-click triggers: submit buttons show immediate state change; disabled controls
  always explain why (tooltip/hint); no double-submit; destructive-looking actions
  (discard a failed reply) confirm only when text would be lost.
- Prefer **undo/forgiveness** over confirmation. There are no destructive server
  operations in the contract (no delete), so confirmations are rare — reserved for
  "discard unsaved draft".

---

## 4. Accessibility (WCAG 2.1 AA) & Unhappy Paths

### 4.1 Accessibility requirements
- **Keyboard:** every flow fully operable by keyboard — browse, open post, open reply
  composer, submit, collapse/expand, load more, continue thread, sign in. Visible focus
  ring on all interactive elements (meets contrast). Logical tab order; no keyboard traps
  in modals (sign-in prompt traps focus while open, restores focus to the trigger on
  close).
- **Comment tree semantics:** render the thread as an accessible tree. Use a `tree` /
  `treeitem` structure (or an equivalent nested `list`) with:
  - `aria-level` = `depth + 1` on each comment node.
  - `aria-expanded` on collapsible nodes; `aria-setsize`/`aria-posinset` where known.
  - The collapse caret is a real `button` with an `aria-label` ("Collapse replies to
    user-9c2").
  - "Continue thread" and "Load more replies" are real buttons/links with descriptive
    labels, not ambiguous "more".
- **Dynamic announcements (`aria-live`):**
  - Optimistic reply insert → polite announcement "Reply posted" (and "Posting reply…"
    on submit).
  - Load-more completion → "10 more posts loaded".
  - Errors (429/503/validation) announced politely; focus moves to the error/first
    invalid field.
- **Forms:** every field has a programmatic `<label>`; counters are associated via
  `aria-describedby`; error messages linked via `aria-describedby` + `aria-invalid`.
- **Color independence:** state (pending/failed/error) never conveyed by color alone —
  always an icon/label too (sober palette makes this essential).
- **Contrast:** AA minimum (4.5:1 body text, 3:1 large text/UI) — enforced by the single
  theme's tokens (Part 2).
- **Reduced motion:** respect `prefers-reduced-motion`; skeleton shimmer and transitions
  degrade to static.
- **Images:** uploaded post images need an alt-text affordance. *Open question for API:
  there's no alt-text field in the contract.* UX recommendation: add an optional
  "Describe this image" field at attach time and store/send it when a field exists; until
  then, render a neutral alt ("Image attached to post") and flag the gap. **Do not ship
  empty alt silently.**
- **Target sizes:** interactive targets ≥ 24×24 CSS px (44×44 recommended on touch).
- **Zoom/reflow:** usable at 200% zoom and 320px width without horizontal scroll (the
  depth-indent cap §2.2 directly serves this).

### 4.2 Unhappy-path catalog (global error → UX mapping)
Map the RFC 9457 `problem+json` to human, actionable UX. Always use `title`/`detail` for
the message when safe, keep `correlationId` available (small, copyable) for support, and
**never leak `type`/stack/raw status to the primary message.**

| Status | When | UX response |
|---|---|---|
| **400** validation | bad create/reply | Map `detail` to the offending field inline; focus first error; keep draft. |
| **401** on write | signed-out or expired token | Non-destructive sign-in prompt; preserve draft + `returnTo`; resume + resubmit same Idempotency-Key. Reads never trigger this. |
| **403** | authorized but forbidden | "You don't have permission to do that." No sign-in loop. |
| **404** | post/comment/route missing | In-app Not Found with Home + Search; for a missing post, specific copy (§2.2). |
| **409** idempotency conflict | retry of an already-applied write | Treat as success; reconcile to the created resource; no scary error. |
| **422** comment depth > 8 | reply beyond cap | "This thread is at its maximum depth. Open it as its own thread to keep replying." + "Continue thread →" (re-root). |
| **429** rate limited | rapid reads/writes | "You're going quickly — try again in Ns." Honor `Retry-After` with a countdown on the action; keep draft; auto-enable retry. |
| **501** search not available | deployment has no search | Disable search affordance via config; if hit, "Search isn't available here." + Home. |
| **503** search degraded | OpenSearch down | Scoped banner: "Search is temporarily unavailable. Browsing still works." + Back to latest. Other reads unaffected. |
| **5xx / network** | transient | "Something went wrong — Retry." Preserve state; retries reuse Idempotency-Key for writes. |

**Rule:** every error state names *what happened* and *what to do next*, keeps the user's
content safe, and offers a path forward. No blank screens, no raw codes in the primary
message.

---

## 5. Minimalist / Sober Visual Direction (hand-off to UI Architect)

> This is **direction, not final tokens.** The UI Architect owns the concrete token
> values, type scale, and component styling. These are the experiential guardrails.

### 5.1 Tone
- **Content-first and calm.** The reading column dominates; chrome recedes. Threadit is a
  place to read and think, not a dashboard. Sober, neutral, quiet — no gamification, no
  loud accents, no vote-score spectacle (and none exists in the contract).

### 5.2 Layout & spacing
- A **single centered reading column** (~65–75ch measure for body text) on a plain
  background. Generous, consistent vertical rhythm; whitespace is the primary structuring
  device, not boxes and borders.
- Cards are defined by spacing and a hairline divider, not heavy shadows or fills.
- Comment nesting uses a **thin thread line + modest indent, capped** (§2.2) so depth is
  legible without crushing the column.

### 5.3 Color (restrained)
- A near-neutral surface, high-contrast ink for text, and **one restrained brand accent**
  used sparingly — for primary actions (Publish/Reply), focus rings, and the logo. Status
  colors (error/warning) are muted and always paired with an icon + text (color-blind
  safe). **No dark/light toggle** — one carefully-tuned light-neutral theme, AA-compliant.

### 5.4 Typography (direction; final system in Part 2)
- **Strong typographic hierarchy carries the design** (since color is restrained):
  - A confident **display/heading** face for post titles and the logo wordmark.
  - A highly readable **text** face for bodies and comments (optimized for long reading).
  - A **mono** face for timestamps/handles/counters/correlation IDs (quiet, technical,
    reinforces the "message board" character).
- Clear scale: Post title (large) › section labels (Comments) › body › meta (handle/time)
  › counters. Line length and line-height tuned for sustained reading.

### 5.5 Brand concept — **Threadit**

> Deliverable per the brief: a concrete logo/brand concept, Reddit-like clone, threaded-
> discussion idea. Final artwork is the UI Architect/designer's; this is the agreed
> concept and rationale.

- **Name treatment:** `Threadit` as a wordmark. The pun is "thread it" (start a thread) —
  lean into the *thread* metaphor, not a mascot.
- **Mark / logomark:** a minimal **"thread" glyph** — a single continuous line that starts
  as a dot (a post) and branches downward-right into two smaller nodes (replies),
  echoing the comment tree's indent + thread-line. One weight, one accent color, works at
  16px (favicon) and large. It literally *is* the nesting line used in the comment UI, so
  brand and interface share one visual idea.
  - Text sketch:
    ```
    ●
    └─ ●
       └─ ●
    ```
    Rendered as a single clean stroke; the top node slightly larger. Monoline, rounded
    joins, sober.
- **Favicon:** the branching-node glyph alone.
- **Logo lockup:** glyph + `Threadit` wordmark, left-aligned, used in the top bar.
- **Voice:** plain, honest, unhurried. Microcopy is calm and human ("You're all caught
  up.", "Reading is always open."). No hype, no exclamation-heavy tone.
- **Configurable:** the wordmark text, glyph accent color, and typefaces are **brand
  tokens** a deployer overrides (Part 2). The *concept* (branching-node = thread) is the
  default identity but the mark is swappable via config/asset slot.

---

## 6. Risks, Anti-Patterns Avoided, Tradeoffs

**Anti-patterns avoided**
- **No numbered pagination** — cursor-only, matching the contract; prevents
  skip/duplicate anomalies on a live feed.
- **No invented endpoints/fields** — no votes, no profiles, no edit/delete, no comment
  images (none exist in the contract). Handles are honestly *derived* from `userId`.
- **No hidden write affordances for lurkers** — show + gate with an explanation beats
  hiding (which confuses). 
- **No silent data loss** — drafts survive 401/429/5xx; failed optimistic nodes stay as
  retry-able, never vanish.
- **No color-only state** — sober palette forces icon+text for all states.
- **No unbounded nesting** — depth cap + indent cap + "continue thread" keep deep threads
  readable on small screens.

**Tradeoffs accepted**
- **Derived handles** (`user-3f9a`) are less human than usernames, but the contract gives
  only `userId`. Flagged as an open question; swappable if a profile endpoint appears.
- **Image flow sequenced after post create** (flow A) because presign is `{post_id}`-
  scoped; image is best-effort. Flagged for API confirmation.
- **`consistent=true` only on the author's first post-read** trades a slightly costlier
  read for a correct read-your-own-write moment, instead of making all reads consistent.
- **Single theme** (per constraint) — we lose user theming choice but gain a tighter,
  more coherent, higher-contrast design and far less complexity. Accepted by requirement.

**Risks to watch**
- OpenSearch lag could surprise authors who search for their own just-posted content;
  mitigated by the persistent EC note, not fully eliminated.
- Deep trees with many branches can still be heavy; collapse/expand + lazy subtree load
  are the mitigations; monitor comment-tree performance (Part 2 handles virtualization if
  needed).
- Alt-text gap for images is an accessibility risk until the contract supports it — flagged.

---

## 7. Dev vs Prod Differences

- **Config/endpoints:** dev may point at a local/stub API and a dev Cognito pool; prod
  uses real `/v1` + prod pool. Same code — only config differs (that's the whole point).
- **Eventual consistency:** dev stubs may be instantly consistent, hiding search-lag and
  read-your-own-write issues. **These flows must be tested against realistic latency** (a
  delayed/degraded search mock), not just the happy stub — otherwise the EC messaging and
  `consistent=true` path go untested.
- **Error states:** must be exercised with injected 401/403/404/409/422/429/501/503, not
  only the success path. Provide a dev affordance to force each `problem+json` status.
- **Image upload:** dev may mock presign + a fake S3; prod does a real cross-origin S3
  PUT — **CORS, size limits, and presign expiry must be verified in a prod-like
  environment**, not just mocked.
- **Auth:** dev convenience sign-in is acceptable, but the **OIDC code+PKCE + callback +
  silent refresh + 401-resume** flow must be validated against real Cognito before
  release.
- **Data volume:** test Home/Search/comment-tree with large datasets and deep threads
  (depth 8 + many branches), not a handful of seed rows, to validate load-more, collapse,
  and the indent cap under real conditions.

---

*End of Part 1 (UX). Part 2 (UI Architecture) follows and implements everything above —
component system, design tokens, final typography system, state/data-fetching, the typed
API client, the configuration layer, auth/token handling, performance, and testing. It
must honor the flows, states, vocabulary, and accessibility contract defined here.*

---
---

> ⬇️ **PART 2 — UI ARCHITECTURE** ⬇️
>
> This part is prescriptive for the implementer. It defines the stack, the exact project
> structure, the two-file configuration layer, the complete design-token set and
> typography system, a concrete Threadit logo (as SVG), every component with its props
> and API binding, the data-fetching layer (TanStack Query) and the typed API client,
> auth/token handling, the performance budget, and the testing strategy. Where Part 2
> shows code, it is **reference illustration** of the intended shape — the implementer
> builds the real thing; it must not deviate from Part 1's behavior.

---

## 2.0 Topology & Rendering Strategy (decisions + rationale)

**Rendering: Client-Side Rendering (CSR) SPA.** Chosen over SSR/SSG.
- *Why:* Reads are public and cacheable, but the app is interactive-first (threaded
  trees, optimistic writes, inline composers, auth). There is no SEO requirement stated,
  no server runtime mandated, and the backend is a separate `/v1` API. A static-hosted
  SPA (S3/CloudFront or any static host) keeps deployment trivial and matches the
  "config in, running app out" directive — no Node server to operate.
- *Rejected:* **Next.js SSR/ISR** — adds a server tier and framework surface we don't
  need; SEO/first-paint gains don't justify the ops cost here. **SSG** — content is
  dynamic and user-generated; prerendering buys little. If SEO on post detail becomes a
  requirement later, revisit with Next.js app-router and a `/posts/:id` server fetch; the
  component system below is framework-portable enough to migrate.

**Topology: modular monolith (single SPA).** No microfrontends.
- *Why:* one small team, one deploy unit, shared design system and API client. Micro-
  frontends would add build/integration cost with zero org-scale justification.
- Structure is modular by **feature** (posts, comments, search, auth, upload) with a
  shared `ui/` component library and shared `lib/` (api client, query layer, config).

**Build tool: Vite.** Fast dev server, first-class TS, easy env handling, tree-shaking,
code-splitting via dynamic `import()` + React Router lazy routes.

**Language: TypeScript, `strict: true`.** The API DTOs are typed end-to-end from the
contract (§2.10). No `any` at the API boundary.

---

## 2.1 Project Structure

```
threadit-web/
├─ index.html                      # title, favicon slot, font <link> (from brand)
├─ .env.example                    # the 6 values a deployer sets (documented)
├─ vite.config.ts
├─ tsconfig.json                   # strict
├─ package.json
├─ public/
│  └─ favicon.svg                  # Threadit branching-node glyph (brand.logo)
└─ src/
   ├─ main.tsx                     # app bootstrap: providers (QueryClient, Router, Auth)
   ├─ App.tsx                      # route tree, layout chrome, ErrorBoundary, Toaster
   │
   ├─ config.ts                    # ← DEPLOYER FILE 1: runtime config from env + flags
   ├─ brand.ts                     # ← DEPLOYER FILE 2: ALL design tokens + logo + type
   │
   ├─ lib/
   │  ├─ api/
   │  │  ├─ client.ts              # typed fetch client: baseUrl + auth + idempotency
   │  │  ├─ types.ts               # DTOs generated from / matching /v1 OpenAPI
   │  │  ├─ problem.ts             # RFC 9457 problem+json parsing + ApiError
   │  │  ├─ posts.ts               # endpoint fns: listPosts, getPost, createPost
   │  │  ├─ comments.ts            # listComments, createComment
   │  │  └─ attachments.ts         # presign, s3Put
   │  ├─ query/
   │  │  ├─ queryClient.ts         # QueryClient config (staleTime, retry policy)
   │  │  ├─ keys.ts                # query key factory (typed, centralized)
   │  │  ├─ usePosts.ts            # useInfinitePosts, usePost
   │  │  ├─ useComments.ts         # useInfiniteComments, useCommentBranch
   │  │  ├─ useCreatePost.ts       # mutation + optimistic nav + consistent read
   │  │  ├─ useCreateComment.ts    # mutation + optimistic tree insert + reconcile
   │  │  └─ useUpload.ts           # presign → S3 PUT with progress
   │  ├─ auth/
   │  │  ├─ AuthProvider.tsx       # OIDC code+PKCE, in-memory access token, refresh
   │  │  ├─ useAuth.ts             # { user, isAuthed, signIn, signOut, getToken }
   │  │  └─ oidc.ts                # Cognito OIDC wiring (config-driven)
   │  ├─ idempotency.ts            # uuid v4 keys, per-attempt reuse-across-retry
   │  ├─ sanitize.ts               # text/markdown sanitization (XSS)
   │  ├─ handle.ts                 # deriveHandle(userId) → "user-3f9a" + avatar glyph
   │  └─ time.ts                   # relative time + <time datetime> helpers
   │
   ├─ ui/                          # shared, token-driven primitives (the design system)
   │  ├─ tokens.css.ts             # CSS variables emitted from brand.ts (single source)
   │  ├─ Button.tsx  Input.tsx  Textarea.tsx  Spinner.tsx  Skeleton.tsx
   │  ├─ Toast.tsx / Toaster.tsx  EmptyState.tsx  ErrorState.tsx  Banner.tsx
   │  ├─ Avatar.tsx  Timestamp.tsx  CharCounter.tsx  Logo.tsx  VisuallyHidden.tsx
   │  └─ ErrorBoundary.tsx
   │
   ├─ components/                  # feature components (compose ui/ + bind to query/)
   │  ├─ layout/   TopBar.tsx  AppLayout.tsx  AuthMenu.tsx  SignInPrompt.tsx
   │  ├─ posts/    PostCard.tsx  PostList.tsx  PostView.tsx  Composer.tsx
   │  ├─ comments/ CommentTree.tsx  CommentNode.tsx  CommentComposer.tsx
   │  ├─ search/   SearchBar.tsx  SearchResults.tsx  EventualConsistencyNote.tsx
   │  └─ upload/   ImageUploader.tsx
   │
   ├─ pages/                       # route components (thin; compose feature components)
   │  ├─ HomePage.tsx  SearchPage.tsx  UserPostsPage.tsx  PostPage.tsx
   │  ├─ NewPostPage.tsx  SignInPage.tsx  SignUpPage.tsx  AuthCallbackPage.tsx
   │  └─ NotFoundPage.tsx
   │
   └─ routes.tsx                   # React Router route table (lazy where heavy)
```

**Dependency direction (enforced):** `pages → components → ui + lib`; `lib` depends only
on `config`/`brand`; `ui` depends only on `brand`/tokens. No feature imports another
feature's internals (go through `lib/query` or shared `ui`). No circular deps.

---

## 2.2 The Configuration Layer (HARD REQUIREMENT)

The whole app is driven by **two files + one env file**. Nothing else needs editing to
stand up a new deployment.

### (a) Runtime config — `src/config.ts` (fed by env)

Vite exposes `import.meta.env.VITE_*`. `config.ts` reads, validates, and freezes them so
the rest of the app imports a typed object (never raw env).

```ts
// src/config.ts  — reference shape
export interface AppConfig {
  apiBaseUrl: string;                 // e.g. "https://api.example.com/v1"
  cognito: {
    region: string;                   // e.g. "eu-west-1"
    userPoolId: string;               // e.g. "eu-west-1_abc123"
    clientId: string;                 // app client id (public SPA client, no secret)
    domain: string;                   // hosted UI domain, e.g. "auth.example.com"
    redirectUri: string;              // e.g. "https://app.example.com/auth/callback"
    scopes: string[];                 // ["openid","email"]
  };
  features: {
    search: boolean;                  // false → hide SearchBar entirely (handles 501)
    images: boolean;                  // false → hide ImageUploader (post has no attach UI)
  };
  upload: {
    maxBytes: number;                 // 5 * 1024 * 1024
    allowedTypes: string[];           // ["image/png","image/jpeg","image/webp"]
  };
  defaults: { lastWindow: 5 | 10 | 20 }; // default recency window on Home (10)
}

function required(name: string, v: string | undefined): string {
  if (!v) throw new Error(`Missing required env ${name}`); // fail fast at boot
  return v;
}

export const config: Readonly<AppConfig> = Object.freeze({
  apiBaseUrl: required("VITE_API_BASE_URL", import.meta.env.VITE_API_BASE_URL),
  cognito: {
    region:      required("VITE_COGNITO_REGION", import.meta.env.VITE_COGNITO_REGION),
    userPoolId:  required("VITE_COGNITO_USER_POOL_ID", import.meta.env.VITE_COGNITO_USER_POOL_ID),
    clientId:    required("VITE_COGNITO_CLIENT_ID", import.meta.env.VITE_COGNITO_CLIENT_ID),
    domain:      required("VITE_COGNITO_DOMAIN", import.meta.env.VITE_COGNITO_DOMAIN),
    redirectUri: import.meta.env.VITE_COGNITO_REDIRECT_URI ?? `${location.origin}/auth/callback`,
    scopes: (import.meta.env.VITE_COGNITO_SCOPES ?? "openid email").split(" "),
  },
  features: {
    search: import.meta.env.VITE_FEATURE_SEARCH !== "false", // default on
    images: import.meta.env.VITE_FEATURE_IMAGES !== "false", // default on
  },
  upload: { maxBytes: 5 * 1024 * 1024, allowedTypes: ["image/png","image/jpeg","image/webp"] },
  defaults: { lastWindow: 10 },
});
```

**Feature-flag behavior (wire these):**
- `features.search === false` → `SearchBar` is not rendered and `/search` renders the
  "Search isn't available here" state (also the response to a `501`).
- `features.images === false` → `ImageUploader` is not rendered in the Composer; create-
  post is text-only.

### (b) Design tokens + brand — `src/brand.ts` (single source of truth)

`brand.ts` holds **all** visual identity. `ui/tokens.css.ts` turns it into CSS custom
properties applied once on `:root`; every component reads `var(--…)` — **no hardcoded
colors, sizes, or font names anywhere else.** Swapping `brand.ts` re-skins the whole app.

```ts
// src/brand.ts — reference shape (final token values in §2.3/§2.4)
export const brand = {
  name: "Threadit",
  wordmark: "Threadit",            // text in the logo lockup
  logo: { /* see §2.5 — accent color + the SVG mark are config-driven */ },

  color: {
    bg:        "#FBFBFA",          // near-neutral paper surface
    surface:   "#FFFFFF",
    ink:       "#1A1A17",          // high-contrast body text
    inkMuted:  "#5C5C57",          // meta (handle/time)
    inkFaint:  "#8A8A83",          // counters, hints
    line:      "#E7E6E1",          // hairline dividers / thread line
    accent:    "#2F6F4F",          // single restrained brand accent (deep green)
    accentInk: "#FFFFFF",          // text on accent
    focus:     "#2F6F4F",          // focus ring (= accent, AA contrast on bg)
    danger:    "#9A2A2A",          // muted error (always paired with icon+text)
    warn:      "#8A5A00",          // muted warning
    successInk:"#2F6F4F",
  },

  font: {
    display: `"Fraunces", Georgia, "Times New Roman", serif`,       // titles + wordmark
    text:    `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`,
    mono:    `"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace`,
  },

  // modular type scale (rem) — see §2.4 for usage mapping
  fontSize: { xs:"0.75rem", sm:"0.875rem", base:"1rem", lg:"1.125rem",
              xl:"1.375rem", "2xl":"1.75rem", "3xl":"2.25rem" },
  lineHeight: { tight:1.2, snug:1.35, normal:1.6, relaxed:1.7 },
  fontWeight: { regular:400, medium:500, semibold:600, bold:700 },

  space: { 0:"0", 1:"4px", 2:"8px", 3:"12px", 4:"16px", 5:"24px",
           6:"32px", 7:"48px", 8:"64px" },               // 4px base scale
  radius: { sm:"4px", md:"8px", lg:"12px", pill:"999px" },
  shadow: { none:"none",
            sm:"0 1px 2px rgba(26,26,23,0.06)",
            md:"0 2px 8px rgba(26,26,23,0.08)" },         // used very sparingly
  breakpoint: { sm:"480px", md:"768px", lg:"1024px" },
  readingColumn: "68ch",                                   // §5.2 measure
  indent: { perLevel:"20px", capLevel:5 },                 // comment-tree indent + cap
  motion: { fast:"120ms", base:"200ms", easing:"cubic-bezier(0.2,0,0,1)" },
} as const;

export type Brand = typeof brand;
```

**Rule for implementers:** if you are about to type a hex color, px size, or font family
inside a component, stop — add/choose a token in `brand.ts` and reference it. The lint
rule (§2.16) forbids raw colors in `components/` and `ui/`.

---

## 2.3 Design Tokens — Full Single-Theme Set

One calm, AA-compliant light-neutral theme. **No dark/light toggle** (explicit
requirement). Values live in `brand.ts`; summarized here with intent.

**Color palette (restrained, neutral + one accent):**

| Token | Value | Use | Contrast |
|---|---|---|---|
| `bg` | `#FBFBFA` | app background (paper) | — |
| `surface` | `#FFFFFF` | cards, composer, menus | — |
| `ink` | `#1A1A17` | body & titles | 14.8:1 on `bg` ✓ AAA |
| `inkMuted` | `#5C5C57` | handles, timestamps | 6.9:1 on `bg` ✓ AA |
| `inkFaint` | `#8A8A83` | counters, hints, disabled | 3.4:1 (large/UI only) |
| `line` | `#E7E6E1` | hairline dividers, thread line | — |
| `accent` | `#2F6F4F` | primary buttons, focus, logo | 5.3:1 on `bg` ✓ AA |
| `accentInk` | `#FFFFFF` | text on accent | 5.3:1 on accent ✓ AA |
| `danger` | `#9A2A2A` | error text/icon (never color-only) | 7.1:1 ✓ AA |
| `warn` | `#8A5A00` | warning text/icon | 5.0:1 ✓ AA |

*Accent is a single deep, quiet green — distinct from Reddit's orange, reads calm/sober.
Deployers can override `accent` only; the palette is tuned so one accent swap keeps AA.*

**Spacing scale (4px base):** `0,4,8,12,16,24,32,48,64` → tokens `space.0…8`. All margins,
padding, and gaps use these — no arbitrary values.

**Radii:** `sm 4px` (inputs, small controls), `md 8px` (cards, composer), `lg 12px`
(modals), `pill` (segmented control, chips). Sober, not rounded-heavy.

**Shadows:** used **very sparingly** (menus/modals/toasts only). Cards use spacing +
hairline `line`, not shadows — reinforces the flat, calm aesthetic.

**Breakpoints:** `sm 480`, `md 768`, `lg 1024`. Mobile-first; the reading column centers
and caps at `readingColumn` (68ch) on wider screens.

**Motion:** `fast 120ms` / `base 200ms`, standard easing. All transitions respect
`prefers-reduced-motion` (disable shimmer + transforms).

---

## 2.4 Brand Typography System

Three Google-Fonts-available typefaces, each with a system fallback stack, loaded with
`font-display: swap` and preconnect to `fonts.gstatic.com`. Subset to Latin; `woff2`.

| Role | Typeface | Fallback stack | Why |
|---|---|---|---|
| **Display** (titles, logo wordmark) | **Fraunces** | `Georgia, "Times New Roman", serif` | A warm, high-contrast serif — gives Threadit a literary, "place to read" character and strong hierarchy without loud color. |
| **Text** (body, comments, UI) | **Inter** | `system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif` | Exceptional screen readability at small sizes, neutral and sober, great for long comment trees and forms. |
| **Mono** (handles, timestamps, counters, correlationId, code) | **IBM Plex Mono** | `ui-monospace, "SF Mono", Menlo, Consolas, monospace` | Quiet technical texture that signals "message board"; disambiguates IDs and counts. |

> All three are swappable via `brand.font.*`. If a deployer sets only their own fonts +
> accent, the app re-skins with zero component edits.

**Modular type scale (usage mapping):**

| Token | Size | Line-height | Weight | Font | Used for |
|---|---|---|---|---|---|
| `3xl` | 2.25rem (36px) | tight | bold | display | — (reserved / marketing) |
| `2xl` | 1.75rem (28px) | tight | semibold | display | **Post title** (detail page) |
| `xl` | 1.375rem (22px) | snug | semibold | display | PostCard title, section "Comments" |
| `lg` | 1.125rem (18px) | normal | regular | text | lead paragraph / emphasis |
| `base` | 1rem (16px) | relaxed (1.7) | regular | text | **Post & comment body** (reading) |
| `sm` | 0.875rem (14px) | normal | regular | text | buttons, inputs, secondary UI |
| `xs` | 0.75rem (12px) | snug | medium | mono | **handles, timestamps, counters, correlationId** |

**Readability rules:** body text uses `font.text` at `base`/1.7 within the 68ch column.
Post titles use `font.display`. Handles/times/counters use `font.mono` at `xs` in
`inkMuted`. Hierarchy is carried by **type + weight + spacing**, not color (per §5.3).

---

## 2.5 Brand & Logo — Threadit (concrete, as SVG)

**Concept:** the pun is *"thread it"* — start a thread. The identity is the **comment
tree itself**: a node that branches into replies. Brand and UI share one glyph — the mark
*is* the thread line used in `CommentNode`. Sober, monoline, one accent color.

**Color usage (restrained):** the mark and wordmark render in `color.ink`; the branching
stroke (or the leading node) uses `color.accent`. One accent, nowhere loud.

### Concept A — Branching Nodes (RECOMMENDED, default)
A single monoline stroke: one larger top node (the post) branches down-right into two
smaller nodes (replies). Rounded joins, one weight. Reads at 16px (favicon) and large.

```svg
<!-- public/favicon.svg & ui/Logo mark — reference -->
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Threadit">
  <!-- post node -->
  <circle cx="6" cy="5" r="2.5" fill="var(--color-accent)"/>
  <!-- thread line branching to replies -->
  <path d="M6 7.5 V14 a3 3 0 0 0 3 3 h4" stroke="var(--color-ink)" stroke-width="1.75"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M6 11 a3 3 0 0 0 3 3 h4" stroke="var(--color-ink)" stroke-width="1.75"
        stroke-linecap="round" stroke-linejoin="round"/>
  <!-- reply nodes -->
  <circle cx="15.5" cy="14"  r="2" fill="none" stroke="var(--color-ink)" stroke-width="1.75"/>
  <circle cx="15.5" cy="17.5" r="2" fill="none" stroke="var(--color-ink)" stroke-width="1.75"/>
</svg>
```

### Concept B — Needle & Thread
A minimal needle whose trailing thread loops into a lowercase "t" / speech-tail. Leans
into the literal "thread/stitch" metaphor. One continuous stroke; the eye of the needle
doubles as a comment dot. Elegant but more decorative — use if the deployer wants warmth.

### Concept C — Nested Chevron Thread
Three right-facing chevrons `›› ›` descending and indenting, echoing nested replies and a
"continue thread →" motion. Extremely minimal, geometric; the most "systemy" of the three.
Good favicon legibility; least distinctive as a wordmark lockup.

**Wordmark treatment:** `Threadit` set in **Fraunces** semibold, tight tracking, `ink`,
with the glyph (Concept A) to its left at cap height. Optional subtle accent on the "t"
descender tie-in. Lockup is left-aligned in the `TopBar`.

```
[◉⌐] Threadit        ← glyph (accent node + ink branches) + Fraunces wordmark
```

**Favicon:** Concept A glyph alone in `favicon.svg` (scales to 16px; the two reply nodes
stay legible). Provide a 180×180 PNG apple-touch fallback generated from the SVG.

**Config:** `brand.logo` exposes `{ markSvg, wordmark, accentOverride? }`. The `Logo`
component renders `brand.logo.markSvg` (defaults to Concept A) + `brand.wordmark`. A
deployer can drop in their own SVG string and wordmark text — no code change.

---

## 2.6 Component System — Catalog with Props & API Bindings

Two layers: **`ui/` primitives** (token-driven, no data) and **`components/` feature
components** (compose primitives, bind to the query layer). Props shown are the intended
public API (reference TS).

### 2.6.1 `ui/` primitives (design system)

| Component | Key props | Notes |
|---|---|---|
| `Button` | `variant: "primary"\|"secondary"\|"ghost"\|"danger"; loading?; disabled?; disabledReason?` | `disabledReason` renders a tooltip/hint (anti-frustration §3.7). `loading` shows `Spinner`, blocks double-submit. |
| `Input` / `Textarea` | `label; value; onChange; error?; describedBy?; maxLength?` | Always labeled; wires `aria-invalid`, `aria-describedby`. |
| `CharCounter` | `value: number; max: number` | Live counter; `warn` near limit, `danger` over; `aria-live="polite"`; linked via `aria-describedby`. |
| `Skeleton` | `lines?; variant: "card"\|"post"\|"comment"` | Matches real geometry; shimmer respects reduced-motion. |
| `Spinner` | `size?; label?` | `role="status"` + visually-hidden label. |
| `EmptyState` | `title; body?; action?` | Calm, centered; `action` is a `Button`/link. |
| `ErrorState` | `title; detail?; correlationId?; onRetry?; retryAfter?` | Non-destructive retry; shows `correlationId` small/copyable; countdown when `retryAfter`. |
| `Banner` | `tone: "info"\|"warn"\|"danger"; dismissible?; action?` | Scoped notices (search-degraded 503, EC note). |
| `Toast`/`Toaster` | `message; tone; duration?` | `aria-live` region; success/undo-style; bottom, unobtrusive. |
| `Avatar` | `userId` | Deterministic glyph/color from `deriveHandle` (§lib). Not a photo. |
| `Timestamp` | `iso: string` | Relative text + `<time datetime>` + absolute in `title`. Mono, `xs`. |
| `Logo` | `size?` | Renders `brand.logo.markSvg` + wordmark; links Home; `aria-label`. |
| `VisuallyHidden` | — | SR-only text helper. |
| `ErrorBoundary` | `fallback` | Catches render errors → `ErrorState` + Home link; logs correlation. |

### 2.6.2 `components/` feature components (with API bindings)

| Component | Props (reference) | API binding | Behavior ref |
|---|---|---|---|
| **`TopBar`** | — (reads `useAuth`, `config.features.search`) | — | §1 chrome. Logo, SearchBar (if `features.search`), New post, AuthMenu. |
| **`AuthMenu`** | — | `useAuth` | Signed-out → "Sign in"; signed-in → handle, "My posts" (`/u/:myId`), "Sign out". §2.7 |
| **`SignInPrompt`** | `reason?: string; returnTo: string` | `useAuth.signIn` | Modal write-gate; focus-trapped; preserves `returnTo` + draft. §2.7 |
| **`PostList`** | `query: { last?; userId?; searchKeyword? }` | `GET /v1/posts` via `useInfinitePosts` | Renders `PostCard[]`; `LoadMore`; skeletons/empty/error. §2.1/§2.6 |
| **`PostCard`** | `post: PostResponse` | (data from list) | Whole-card link → `/posts/:id`; nested author link → `/u/:userId`; image indicator. §2.1 |
| **`PostView`** | `postId: string; consistent?: boolean` | `GET /v1/posts/{id}` via `usePost` | Title/meta/body + optional image (lazy); "Reply to post". `consistent` on author's first read. §2.2/§3.1 |
| **`Composer`** (post) | `onPublished(id)` | `useCreatePost` → `POST /v1/posts` (+ `useUpload`) | Title/body + counters + `ImageUploader`; Idempotency-Key; optimistic nav. §2.3 |
| **`CommentTree`** | `postId: string` | `GET /v1/posts/{id}/comments` via `useInfiniteComments` | Builds tree from flat thread-ordered items (`parentId`/`depth`/`rootCommentId`); top-level `LoadMore`. `role="tree"`. §2.2 |
| **`CommentNode`** | `comment; childrenNodes; depth; onReply` | `useCommentBranch` (lazy subtree via `rootCommentId`) | Indent+thread-line (capped), collapse/expand (`aria-expanded`), per-branch "Load more replies", depth-8 → "Continue thread →". `role="treeitem"`, `aria-level=depth+1`. §2.2/§3.4 |
| **`CommentComposer`** | `postId; parentId: string\|null; replyingTo?; onPosted; onCancel` | `useCreateComment` → `POST …/comments` | Inline; context header; counter; optimistic insert + reconcile; 422→continue-thread. §2.4 |
| **`ImageUploader`** | `postId: string; onUploaded(objectKey); onError` | `useUpload` → `attachments:presign` then S3 `PUT` | Type/size pre-check (`config.upload`), thumbnail, determinate progress, re-presign on retry. Hidden if `!features.images`. §2.5 |
| **`SearchBar`** | `initialQuery?` | navigates `/search?q=` | Collapses to icon on mobile; hidden if `!features.search`. §1/§2.6 |
| **`SearchResults`** | `q: string` | `GET /v1/posts?search_keyword=` via `useInfinitePosts` | Reuses `PostCard`/`LoadMore`; EC note; 503 banner; 501 → unavailable. §2.6 |
| **`EventualConsistencyNote`** | — | — | Persistent info banner on active search. §2.6/§3.2 |
| **`LoadMore`** | `hasMore; isLoading; onLoadMore; endLabel?` | (drives infinite query) | Cursor-only; inline spinner; disabled while fetching; quiet end marker when no `nextCursor`. §3.3 |
| **`NotFound`** | `title?; body?` | — | In-app 404 with Home + Search. §2.2 |

> There is intentionally **no** `Vote`, `Sort`, `EditPost`, `DeleteComment`, or
> `CommentImage` component — none exist in the contract (§0 assumptions).

---

## 2.7 State Management & Data Flow

Four state categories, each with a deliberate owner:

| Category | Owner | Examples |
|---|---|---|
| **Server state** | **TanStack Query** | posts list, post, comment tree/branches, mutations |
| **URL state** | **React Router** | `?q`, `?last`, `/u/:userId`, `/posts/:id`, `#c-:id`, `returnTo` |
| **Global client state** | **AuthProvider (React context)** | session, user, access token (in memory) |
| **Local UI state** | component `useState` | composer open/closed, collapse toggles, upload progress |

**No Redux / no global store.** Server state belongs in Query; UI state is local; the only
shared client state is auth. This avoids over-globalizing (Part 1 §state rationale).

### TanStack Query configuration (`lib/query/queryClient.ts`)
- `staleTime`: lists `30s`, single post `15s` (public reads are cacheable; keep it fresh
  but avoid refetch storms).
- `gcTime`: `5m`. `refetchOnWindowFocus: false` for lists (calm UX; no surprise reshuffles),
  `true` is acceptable for a single post.
- **Retry policy:** retry network/5xx up to 2× with exponential backoff + jitter; **never
  retry 4xx** (400/401/403/404/409/422) — those are terminal and handled by UX. For
  **429**, do not auto-retry blindly; surface Retry-After and let the user/countdown drive.
- **Writes keep the same Idempotency-Key across Query's internal retries** (the key is
  created once per mutation attempt in `useCreatePost`/`useCreateComment`; see §2.9).

### Query key factory (`lib/query/keys.ts`)
```ts
export const qk = {
  posts: (f: { last?: number; userId?: string; q?: string }) => ["posts", f] as const,
  post:  (id: string, consistent?: boolean) => ["post", id, { consistent: !!consistent }] as const,
  comments: (postId: string) => ["comments", postId] as const,
  commentBranch: (postId: string, rootId: string) => ["comments", postId, "branch", rootId] as const,
};
```

### Infinite lists (cursor "load more")
`useInfinitePosts` / `useInfiniteComments` use `useInfiniteQuery` with
`getNextPageParam: (last) => last.nextCursor ?? undefined`. `LoadMore` calls
`fetchNextPage()`; absence of `nextCursor` → `hasNextPage=false` → end marker. **Pages are
appended; already-loaded content is never discarded** (§3.3). Back-navigation restores the
list from Query cache (keep pages in `gcTime`).

### Comment tree build
`GET …/comments` returns a **flat array in thread order** (materialized path). `CommentTree`
reduces it into a nested structure keyed by `parentId`/`rootCommentId`, honoring `depth`.
Lazy branches (`CommentNode` → `useCommentBranch(postId, rootCommentId)`) fetch with
`rootCommentId` + cursor and merge into the node's children. **Collapse state is local UI
state** (not server), keyed by comment id, preserved while mounted.

### Optimistic UI + reconciliation
- **Create comment** (`useCreateComment`): `onMutate` inserts a temp node (temp id,
  `status:"sending"`) into the correct branch of the `comments` cache; `onSuccess` swaps the
  temp node for the real `CommentResponse`; `onError` marks the temp node `status:"failed"`
  (Retry/Discard) — **never rolls back silently** (Part 1 §2.4). Announce via `aria-live`.
- **Create post** (`useCreatePost`): no in-list optimism needed; on `201` navigate to
  `/posts/:id` and `PostView` does its **first read with `?consistent=true`** (read-your-
  own-write, §3.1), then normal reads after.
- **409** in any mutation → `onSuccess`-equivalent (treat as already-applied; reconcile to
  the resource), not an error (§3.5).

---

## 2.8 The Typed API Client

A thin `fetch` wrapper — **the only place `apiBaseUrl` and the auth token plug in.** DTOs
in `lib/api/types.ts` match the `/v1` OpenAPI contract (generate with
`openapi-typescript` if a spec file is provided; otherwise hand-write to §2.10 exactly).

```ts
// lib/api/client.ts — reference
import { config } from "../../config";
import { parseProblem, ApiError } from "./problem";

export interface RequestOpts {
  method?: string;
  body?: unknown;
  token?: string;          // access JWT (writes only); omitted on public reads
  idempotencyKey?: string; // writes only
  query?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
}

export async function apiFetch<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const url = new URL(config.apiBaseUrl + path);
  for (const [k, v] of Object.entries(opts.query ?? {})) {
    if (v !== undefined) url.searchParams.set(k, String(v));
  }
  const headers: Record<string, string> = { "Accept": "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;        // writes
  if (opts.idempotencyKey) headers["Idempotency-Key"] = opts.idempotencyKey; // writes

  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });
  if (!res.ok) throw await parseProblem(res);   // → typed ApiError (status, title, detail, correlationId, retryable, retryAfter)
  return res.status === 204 ? (undefined as T) : (await res.json()) as T;
}
```

Endpoint functions (reference — match the contract exactly, §2.10):
```ts
// posts.ts
export const listPosts = (q, token?) =>
  apiFetch<PageResponse<PostResponse>>("/posts", { query: q, token });
export const getPost = (id, consistent?, token?) =>
  apiFetch<PostResponse>(`/posts/${id}`, { query: { consistent }, token });
export const createPost = (body: CreatePostRequest, token: string, idempotencyKey: string) =>
  apiFetch<PostResponse>("/posts", { method: "POST", body, token, idempotencyKey });

// comments.ts
export const listComments = (postId, q) =>
  apiFetch<PageResponse<CommentResponse>>(`/posts/${postId}/comments`, { query: q });
export const createComment = (postId, body: CreateCommentRequest, token, idempotencyKey) =>
  apiFetch<CommentResponse>(`/posts/${postId}/comments`, { method:"POST", body, token, idempotencyKey });

// attachments.ts
export const presign = (postId, body: PresignRequest, token) =>
  apiFetch<PresignResponse>(`/posts/${postId}/attachments:presign`, { method:"POST", body, token });
export const s3Put = (url, file, onProgress) => /* XHR PUT for upload progress; raw bytes; Content-Type = file.type */;
```

**Problem+json parsing (`problem.ts`):** on non-2xx, read `application/problem+json`
`{type,title,status,detail,correlationId,retryable}`, read `Retry-After` header for 429,
and throw a typed `ApiError`. The UX layer maps `ApiError.status` to the table in Part 1
§4.2. **Never surface `type`/stack in the primary message.**

---

## 2.9 Idempotency, Auth & Token Handling

### Idempotency (`lib/idempotency.ts`)
- `newKey()` → UUID v4 (`crypto.randomUUID()`).
- Each mutation **attempt** creates one key, stored in the mutation's closure, and reused
  across TanStack Query's internal retries and manual retries of that same attempt. A new
  user-initiated submit → new key. **409 is treated as success** (§3.5). (Part 1 §3.5.)

### Auth (`lib/auth/AuthProvider.tsx`, Cognito OIDC)
- **Flow:** Authorization Code + **PKCE** against the Cognito user-pool hosted UI
  (config-driven: `cognito.domain`, `clientId`, `redirectUri`, `scopes`). `/signin` and
  `/signup` kick off the redirect; `/auth/callback` exchanges the code for tokens.
  *(Open question from Part 1: hosted UI vs embedded — default to hosted UI; it avoids
  duplicating pool password policy. Embeddable later behind the same `useAuth` API.)*
- **Token storage (security):**
  - **Access token (JWT) is held in memory only** (React state inside `AuthProvider`) —
    **never `localStorage`/`sessionStorage`** (XSS exfiltration risk). It is injected into
    writes via `useAuth.getToken()`.
  - **Refresh token:** prefer the browser to hold it as an **httpOnly, Secure, SameSite
    cookie** if the deployment fronts Cognito with a token endpoint that can set one;
    otherwise use Cognito's refresh via the hosted session and **silent re-auth**
    (hidden iframe / `prompt=none`) to re-obtain an access token. Do **not** persist the
    refresh token in JS-readable storage. *(Flag: if the SPA must self-manage refresh
    tokens with no cookie backend, document the residual XSS risk and keep them in memory,
    accepting re-login on full reload.)*
  - **On full page reload:** attempt silent re-auth; if it fails, the user is signed out
    (reads still work; writes re-prompt). This is the accepted tradeoff of not persisting
    tokens in JS storage.
- **401 on a write:** the client throws `ApiError(401)`; the write boundary catches it,
  preserves the draft + intent, opens `SignInPrompt`, and on success **resubmits the same
  draft with the same Idempotency-Key** (Part 1 §2.3/§3.6).
- `useAuth` surface: `{ user: { userId } | null, isAuthed, signIn(returnTo), signOut(),
  getToken(): Promise<string> }`. `userId` comes from the ID token's `sub` — **never from
  any form field** (contract: userId derives from the token).

### XSS / sanitization (`lib/sanitize.ts`)
- Post/comment **body is user-generated text.** React escapes by default — **do not use
  `dangerouslySetInnerHTML` on raw user content.**
- If light markdown rendering is desired, render through a safe pipeline
  (`marked`/`markdown-it` → **DOMPurify** with a strict allowlist: no `script`,
  `iframe`, `on*` handlers, `javascript:` URLs; links `rel="noopener noreferrer"` and
  `target` constrained). Otherwise render as plain text with preserved line breaks.
- A strict **CSP** is recommended at the host: `default-src 'self'`; `img-src 'self'
  <s3-bucket-domain> data:`; `connect-src 'self' <api-origin> <cognito-domain>`;
  `font-src fonts.gstatic.com`; `style-src 'self' 'unsafe-inline'` (or nonce); no inline
  scripts. Document the exact origins (API, S3, Cognito, fonts) as deploy config.
- Uploaded image is referenced by URL only; never execute or inline untrusted bytes.

---

## 2.10 Backend Contract — Types the Client Binds To (do not invent)

Hand-written or generated to match the `/v1` contract **exactly** (Part 1 §0–§2):

```ts
// lib/api/types.ts — reference, matches the contract
export interface PageResponse<T> { items: T[]; nextCursor: string | null; limit: number; }

export interface PostResponse {
  id: string; title: string; body: string;
  userId: string; createdAt: string; updatedAt: string;
}
export interface CreatePostRequest { title: string; body: string; } // 1..300 / 1..40000

export interface CommentResponse {
  id: string; postId: string; userId: string; text: string;
  depth: number; parentId: string | null; rootCommentId: string | null; createdAt: string;
}
export interface CreateCommentRequest { text: string; parentId?: string | null; } // text 1..10000

export interface PresignRequest  { contentType: string; sizeBytes: number; }
export interface PresignResponse { url: string; objectKey: string; expiresIn: number; }

export interface Problem {        // RFC 9457 problem+json
  type: string; title: string; status: number; detail?: string;
  correlationId?: string; retryable?: boolean;
}
```

**Endpoint → component → hook map:**

| Endpoint | Hook | Component |
|---|---|---|
| `GET /v1/posts` (`limit,cursor,user_id,search_keyword,last`) | `useInfinitePosts` | `PostList`, `SearchResults`, `UserPostsPage` |
| `POST /v1/posts` (JWT + Idempotency-Key) | `useCreatePost` | `Composer` |
| `GET /v1/posts/{id}` (`?consistent=true`) | `usePost` | `PostView` |
| `GET /v1/posts/{id}/comments` (`limit,cursor,rootCommentId`) | `useInfiniteComments` / `useCommentBranch` | `CommentTree` / `CommentNode` |
| `POST /v1/posts/{id}/comments` (JWT + Idempotency-Key) | `useCreateComment` | `CommentComposer` |
| `POST /v1/posts/{id}/attachments:presign` (JWT) → S3 `PUT` | `useUpload` | `ImageUploader` |

Query param names are sent **exactly** as the contract: `user_id`, `search_keyword`,
`last`, `cursor`, `limit`, `rootCommentId`, `consistent`.

---

## 2.11 Rendering, Performance & Loading

**Performance budget (enforced in CI via Lighthouse / bundle-size check):**
- **JS (initial route, gzipped):** ≤ **170KB**. Route-split so Home ships only what it
  needs; `/new`, auth, and upload are lazy chunks.
- **Core Web Vitals (field targets):** **LCP ≤ 2.5s**, **INP ≤ 200ms**, **CLS ≤ 0.1**.
- **TTI** on Home ≤ 3.5s on mid-tier mobile / Slow 4G.

**How we hold it:**
- **Code-splitting:** `React.lazy` + Router lazy routes for `NewPostPage`, auth pages,
  `ImageUploader` (and its upload XHR logic), and any markdown/DOMPurify pipeline (loaded
  only when rendering bodies that need it).
- **Tree-shaking:** ES modules; avoid barrel files that defeat shaking; import icons
  individually.
- **Skeletons preserve layout** (Part 1) → protects **CLS**. Reserve image space with
  width/height/aspect-ratio to avoid shift when the post image loads.
- **Images:** post images `loading="lazy"`, `decoding="async"`, constrained to the reading
  column; served from S3 (optionally via CDN). Thumbnails for the composer use object URLs
  (revoked on unmount).
- **Fonts:** `font-display: swap`, preconnect, Latin subset, `woff2`; fallback stacks keep
  text visible immediately (no FOIT) and limit CLS (size-adjust metrics where possible).
- **Prefetch:** on `PostCard` hover/focus, prefetch `getPost(id)` via Query to make detail
  navigation feel instant (desktop only; respect data-saver).
- **List weight:** cursor "load more" keeps initial payloads small. **Comment-tree
  virtualization** is deferred (adds complexity and fights the collapse/indent model) —
  collapse/expand + lazy subtree load are the first-line mitigations. **If profiling shows
  jank on very large trees, introduce windowed rendering of top-level branches** (flagged
  as the escalation path, not built by default).

---

## 2.12 Cross-Browser & Cross-Device Strategy
- **Matrix:** last 2 versions of Chrome, Firefox, Safari (incl. iOS Safari), Edge. No IE.
- **Baseline APIs used:** `fetch`, `crypto.randomUUID`, `URL`, CSS custom properties,
  flexbox/grid, container-free responsive via breakpoints — all supported across the matrix; no
  polyfills required. Feature-detect `crypto.randomUUID` with a tiny fallback for older
  Safari.
- **Responsive:** mobile-first; single reading column centered and capped at
  `readingColumn`. `SearchBar` collapses to an icon < `md`. Comment indent uses the capped
  scheme so deep threads never cause horizontal scroll at 320px (Part 1 §4.1).
- **Progressive enhancement:** core reading works without JS? No — it's an SPA; but all
  interactive targets are real `<a>`/`<button>` for keyboard + SR correctness.

---

## 2.13 Accessibility Implementation (how the UX contract is met in code)
Implements Part 1 §4.1. Baked into `ui/` so screens inherit it:
- **Comment tree:** `CommentTree` = `role="tree"`; `CommentNode` = `role="treeitem"` with
  `aria-level={depth+1}`, `aria-expanded` on collapsible nodes, `aria-setsize/posinset`
  where known. Collapse caret is a real `<button>` with `aria-label`. "Continue thread"
  and "Load more replies" are labeled buttons.
- **Live regions:** a single app-level polite `aria-live` region (via `Toaster`/announcer)
  for "Reply posted", "10 more posts loaded", and error announcements; focus moves to the
  first invalid field on validation error.
- **Forms:** `Input`/`Textarea` enforce `<label>`, `aria-invalid`, `aria-describedby`
  (counter + error) by construction — can't ship an unlabeled field.
- **Focus management:** `SignInPrompt` traps focus and restores to trigger on close; route
  changes move focus to the main `<h1>`; `#c-:commentId` deep link scrolls + focuses +
  highlights the target comment.
- **Color independence:** pending/failed/error always carry an icon + text, never color
  alone (sober palette makes this mandatory).
- **Reduced motion:** tokens gate shimmer/transitions on `prefers-reduced-motion`.
- **Alt text:** `ImageUploader` SHOULD expose an optional "Describe this image" field;
  until the contract carries it, render a neutral alt and keep the field value client-side.
  **Flagged gap (Part 1 open question d).**
- **Targets:** ≥24×24 CSS px (44×44 on touch); zoom/reflow usable at 200% and 320px.

---

## 2.14 Validation & Error Architecture (aligned to the contract)
- **Client validation mirrors the contract** (title 1..300, body 1..40000, comment text
  1..10000, image type/≤5MB) — but the **server 400 is the source of truth**; map its
  `detail` to the offending field and focus it.
- **Central error mapping:** one `mapApiError(error, context)` turns an `ApiError` into the
  Part 1 §4.2 UX (component + copy + action). Used by every mutation and query error path
  so behavior is consistent (401→SignInPrompt+resume, 409→success, 422→continue-thread,
  429→Retry-After countdown, 501→search-off, 503→scoped banner, 404→in-app NotFound,
  5xx→retry). `correlationId` surfaced small/copyable; raw `type`/stack never shown.
- **ErrorBoundary** wraps the route tree for render-time errors → `ErrorState` + Home.

---

## 2.15 Routing & Navigation (implements Part 1 §1)
React Router v6 with the route table in `routes.tsx` mirroring Part 1's map (`/`,
`/search`, `/u/:userId`, `/posts/:postId` + `#c-:commentId`, `/new`, `/signin`, `/signup`,
`/auth/callback`, `*`). Auth-gated `/new` uses a guard that redirects to `/signin?returnTo=`
when `!isAuthed`. URL owns filter state (`?q`, `?last`). Scroll restoration on back; focus
to `<h1>` on navigation. All lists/details are shareable deep links.

---

## 2.16 Testing & Quality Strategy
- **Unit (Vitest + React Testing Library):** `ui/` primitives, `deriveHandle`, `sanitize`,
  idempotency key reuse, comment-tree builder (flat thread-order → nested), `mapApiError`.
- **Integration (RTL + MSW):** mock `/v1` with **MSW**; test each flow against the real
  DTO shapes and each error status (400/401/403/404/409/422/429/501/503) — including
  optimistic insert + reconcile, 409-as-success, 401-resume-with-same-key, 503 search
  banner, consistent-read on author's first post view.
- **E2E (Playwright):** critical journeys — browse+load more, open post+expand tree+
  continue-thread, sign in (against a Cognito test pool or stub), create post+reply
  (optimistic), image upload (mock presign + fake S3, plus one real prod-like run), search
  with EC note.
- **Accessibility:** `axe` in integration + Playwright; keyboard-only pass on every flow;
  tree ARIA assertions.
- **Visual regression:** Playwright snapshots of key screens + states (loading/empty/
  error) to lock the sober visual system.
- **Contract alignment:** if an OpenAPI spec is provided, generate `types.ts` with
  `openapi-typescript` in CI so drift fails the build; otherwise a contract test asserts
  the hand-written types against recorded fixtures.
- **Lint guard:** ESLint rule forbidding raw hex colors / px font-sizes / font-family
  literals in `components/` and `ui/` (must use tokens) — enforces configurability.
- **CI gates:** typecheck, lint, unit+integration, Lighthouse budget (§2.11), bundle-size
  check.

---

## 2.17 Getting Started — Plug In These 6 Values and Run

A new deployer edits **one env file** (6 required values) and optionally **`brand.ts`**,
then builds. No component code is touched.

**Step 1 — set the 6 values in `.env` (copy from `.env.example`):**
```bash
VITE_API_BASE_URL=https://api.yourdomain.com/v1   # 1) API base (includes /v1)
VITE_COGNITO_REGION=eu-west-1                       # 2) Cognito region
VITE_COGNITO_USER_POOL_ID=eu-west-1_abc123          # 3) user pool id
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxx         # 4) SPA app client id (no secret)
VITE_COGNITO_DOMAIN=auth.yourdomain.com             # 5) hosted UI domain
VITE_COGNITO_REDIRECT_URI=https://app.yourdomain.com/auth/callback  # 6) OIDC redirect
# optional flags (sensible defaults):
# VITE_FEATURE_SEARCH=true     # false → hide search + handle 501
# VITE_FEATURE_IMAGES=true     # false → text-only posts
```

**Step 2 — (optional) brand it in `src/brand.ts`:** set `wordmark`, `color.accent`,
`font.{display,text,mono}`, and drop your `logo.markSvg`. Everything re-skins from tokens.

**Step 3 — run:**
```bash
npm install
npm run dev        # local dev against the configured API
npm run build      # production static bundle (dist/) for S3/CloudFront or any static host
npm run preview    # verify the production build locally
```

**That's it:** valid endpoints + Cognito values (and optionally brand) → a working
Threadit. Missing a required env var fails fast at boot with a clear message (§2.2a).

---

## 2.18 Scalability & Evolution
- **Codebase scales by feature folders** with a one-way dependency graph; new surfaces
  (e.g., a profile page if a display-name endpoint appears) slot in without touching
  existing features.
- **Contract evolution:** DTOs are centralized in `lib/api/types.ts` (ideally generated),
  so an additive contract change is a one-file update + new hook. The open questions from
  Part 1 (display-name lookup, image sequencing, hosted-vs-embedded auth, alt-text field)
  each have a clearly isolated change site noted above.
- **Theming/white-label:** because all identity is in `brand.ts`, multiple branded
  deployments are a config swap — the only "tenant-like" dimension (Part 1 §0 assumption 6).
- **Deploy:** static hosting + CDN; immutable hashed assets; `index.html` no-cache so new
  bundles roll out instantly; env baked at build time (one build per environment) or
  injected via a runtime `config.js` if a single artifact across envs is required (flag
  the choice at build setup).

---

## 2.19 UI Risks, Anti-Patterns Avoided, Tradeoffs
**Avoided:** global store sprawl (Query owns server state); hardcoded styling (tokens +
lint guard); `dangerouslySetInnerHTML` on raw user text (sanitized pipeline or plain
text); tokens in `localStorage` (in-memory access token); numbered pagination (cursor
only); over-fetching (consistent-read only on author's first post view).
**Tradeoffs accepted:** CSR (no SSR/SEO) for ops simplicity; in-memory token → re-auth on
hard reload if silent refresh fails; comment-tree virtualization deferred (collapse + lazy
subtree first); hosted Cognito UI (less control, no password-policy duplication).
**Risks watched:** very large/deep comment trees (escalate to windowing); S3 CORS/presign
expiry (must be verified prod-like, Part 1 §7); font loading CLS (mitigated via swap +
fallback metrics).

---

## 2.20 Dev vs Prod (UI specifics, complements Part 1 §7)
- **Dev:** MSW mocks `/v1` (incl. injectable error statuses + artificial latency to
  exercise EC and consistent-read); a dev sign-in shim is acceptable. Vite dev server.
- **Prod:** real `/v1`, real Cognito OIDC (code+PKCE, callback, silent refresh), real
  cross-origin S3 PUT (CORS + presign expiry verified), strict CSP, Lighthouse budget
  enforced, static bundle on CDN. **Same code — only `config.ts`/env + `brand.ts` differ.**

---

*End of Part 2 (UI Architecture) and of the Threadit Frontend Build Prompt. Together,
Part 1 (UX) and Part 2 (UI) are a single, self-contained, implementation-ready
specification: configure `src/config.ts` + `src/brand.ts`, honor the flows/states/
accessibility of Part 1 and the component/data/token architecture of Part 2, and build.*

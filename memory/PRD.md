# Jomp Trade — PRD (Internal Living Doc)

## 1. Original Problem Statement
Build a web-based SaaS — originally the Helix Platform, now rebranded to **Jomp Trade** — a unified export management, compliance, and cross-border financial transactions platform for Nigerian / African businesses trading with the United States. Banking partner: Anchor (`getanchor.co`). Operated by Riby Inc (US) + JompStart Digital (Nigeria) with DobbleHelix Limited as the originating parent. Focus sectors: fashion & textiles, agriculture, staple foods, general goods.

Full source: `Helix_Platform_PRD.md` (PRD v1.0 MVP).

## 2. User Personas
- **Exporter** (primary) — Nigerian manufacturer / agro-processor. Needs: catalog, compliance, USD account, buyer verification.
- **Buyer** (US importer) — needs verified African suppliers, payment execution.
- **Admin / Super Admin** — DobbleHelix / Riby ops. Verification queue, disputes, financial overview.

## 3. Architecture (as built, Feb 2026)
- **Backend**: FastAPI + motor (MongoDB).
- **Frontend**: React 19 + React Router 7 + shadcn + Tailwind, Command Center dark theme (navy #0A1628, gold #C9922A, teal #1A7A6E), Inter + JetBrains Mono fonts, left-rail nav.
- **Auth**: dual — JWT email/password + Emergent Google OAuth. Roles: exporter, buyer, admin, super_admin.
- **Banking**: Full GetAnchor integration layer (`anchor_client.py`) with `ANCHOR_ENV=sandbox_mock` — all Anchor API calls return realistic mock data and are logged with `[MOCK]`. Swap to `ANCHOR_ENV=sandbox`/`live` + real `ANCHOR_API_KEY` to go real with zero code change.
- **Emails**: Resend (DobbleHelix key set).
- **Object Storage**: Emergent object storage (product photos, KYC docs, compliance docs, generated PDFs).
- **PDFs**: ReportLab — proforma invoice, commercial invoice, packing list, certificate of origin.
- **FX**: open.er-api.com free public API (cached 30 min).

## 4. Modules Implemented (MVP complete)
### 4.1 Onboarding & Verification
- `POST /api/businesses` creates business profile + auto-creates Anchor customer (mock).
- `POST /api/businesses/{id}/kyb` + `/kyc` submits docs for review.
- `GET /api/admin/verifications`, `POST /api/admin/verifications/{id}/decide` — admin queue. On approval, NGN+USD deposit accounts are auto-provisioned.
- Email notifications on decision via Resend.

### 4.2 Product & Export Catalog
- Full CRUD `/api/products`. Exporter can create/edit/archive. Buyers browse public marketplace.
- Auto-calculates NGN price from USD via FX feed on save.
- Compliance badges & export readiness score displayed.

### 4.3 Trade & Order Management
- `POST /api/rfq` (buyer) → draft order.
- `POST /api/orders/{id}/proforma` (supplier) → confirmed + creates Anchor reserved account.
- `POST /api/orders/{id}/simulate-payment` (mock substitute for Anchor `account.credited` webhook) creates credit tx + 1% platform fee.
- `POST /api/orders/{id}/status` advances lifecycle: draft → confirmed → in_production → ready_to_ship → shipped → delivered (+ disputed).
- `GET /api/orders/{id}/pdf/{proforma|commercial|packing|origin}` generates PDF via ReportLab on demand.
- Disputes: `/api/orders/{id}/dispute`, admin resolution queue.

### 4.4 Compliance Vault
- Document upload + expiry tracking (active / expiring_soon / expired / pending_review).
- Per-business compliance score (0–100) computed from required docs for listed product categories.
- Category-specific US import guides (FDA / USDA / CBP).
- 30d / 7d expiry alerts (scheduled emails — wired, callable ad-hoc).

### 4.5 Financial Management
- NGN + USD balances derived from ledger.
- Transaction history with filters (currency, type).
- NIP withdrawal flow (mock transfer + debit tx).
- Admin overview: volume by currency, sector mix, fees collected.

## 5. Seed Data
- `admin@helix.com` (super_admin)
- `exporter@helix.com` — Lagos Heritage Textiles Ltd (NG, approved)
- `buyer@helix.com` — Brooklyn Heritage Imports LLC (US, approved)
- 6 products, 2 orders (1 paid, 1 pending), 4 compliance docs (incl. 1 expiring_soon).
- All demo passwords: `Helix@123`.

## 6. What's been implemented (log)
- **2026-02-22**: Full MVP shipped — 5 modules end-to-end, Anchor MOCKED, 25/25 backend tests passing.
- **2026-02-23**: JompStart added as 4th operating partner + business credit module (apply → admin decision → accept → disburse). Emergent badge removed, favicon swapped, partner footers updated everywhere.
- **2026-02-23 (pm)**: (a) JompStart **repayment scheduling + auto-debit** — monthly amortized schedule at accept, auto-deducts from incoming USD (trade payments AND consumer sales) toward next-due installment. (b) Separate **`jompstart_admin` role** — scoped to `/admin/credit` only, 403 on disputes/verifications/finance. (c) **Consumer e-commerce module** — public `/shop` storefront, two listing modes: `buyer_local` (US-stocked, 48-hour) and `riby_dtc` (direct from Africa with Riby Inc as Delivery Partner of Record). Full checkout (2% platform fee), fulfillment queue, consumer role. 10/10 follow-up tests passing, critical bug (duplicate kwarg on listing create) found and fixed; atomic stock decrement; simulate-payment resilient.
- **2026-02-24**: Rebranded Helix → **Jomp Trade**. Added **Riby Inc escrow** for all consumer orders (funds held at checkout, released on delivery confirm/seller mark-delivered). Added **Quote-then-Prepay** flow (`/api/shop/quotes` request → seller responds → consumer accepts → escrow checkout). JompStart auto-debit now runs at escrow RELEASE rather than payment (reflects real cash flow).
- **2026-02-24 (pm)**: Iteration 6 stabilization — fixed double-counted 2% marketplace fee bug in `_release_escrow` (credit_tx now gross, fee_tx is the sole 2% debit → seller wallet net = total*0.98 exactly). Quote decline now status-guarded (only pending/quoted). Quote-prepay checkout rejects quantity mismatch (400). `create_quote` restricted to `consumer`/`admin` roles and blocks self-quotes. `accept_offer` collapsed to single update_one and response renamed `transaction_id`→`disbursement_tx_id`. Per-product unique Unsplash images + fallback on `<img onError>`. **Light / Dark theme toggle** wired via `ThemeProvider` + `ThemeToggle` (Sun/Moon button) in Shell, ShopShell, Landing; light theme uses Jomp Icon palette (purple #4A2E8A + orange #F39C12 + white). 29/29 pytest pass across iter5+iter6.

## 7. Backlog / Next up

### P0 — pre-launch
- Flip ANCHOR_ENV to `sandbox` once user provides `ANCHOR_API_KEY` and the Anchor dashboard webhook is pointed at `/api/webhooks/anchor`.
- Verify Resend sender domain (currently `onboarding@resend.dev` placeholder; switch to dobblehelix.com once DNS verified).
- Scheduled email job for 30d/7d compliance expiry alerts (cron / apscheduler).

### P1 — early revenue / growth enhancers
- Stripe-style auto-topup view for Anchor-held USD (+ optional crypto off-ramp via Stripe Crypto).
- Bulk transfers (`/api/transfers/bulk`) for end-of-day settlement batch.
- Custom per-business fee tiers.
- Buyer-side saved suppliers + repeat-order templates.
- Messaging thread per order.

### P2
- Shipping integration (DHL/Flexport) woven into order status.
- SMS via Termii for Nigerian users.
- Multi-country expansion (Ghana, Kenya, SA).
- AI compliance assistant over Anchor MCP.
- Export trade financing.

## 8. Environment variables
Managed in `/app/backend/.env`:
`MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `JWT_ALG`, `JWT_EXPIRE_HOURS`, `ANCHOR_API_KEY` (empty in mock), `ANCHOR_WEBHOOK_SECRET`, `ANCHOR_ENV=sandbox_mock`, `ANCHOR_SANDBOX_URL`, `ANCHOR_LIVE_URL`, `RESEND_API_KEY`, `SENDER_EMAIL`, `EMERGENT_LLM_KEY`, `APP_NAME`, `APP_URL`, `EXCHANGE_RATE_API`.

## 9. Compliance note
- NDPR (Nigeria) — PII encrypted at rest via storage provider.
- CBN — no unlicensed FX conversion; NGN/USD accounts are Anchor-issued.
- FinCEN BSA — platform fee & transaction audit log in place.

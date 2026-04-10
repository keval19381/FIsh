# Workspace

## AquaBasket

A production-ready AquaBasket web platform built with Python Flask + SQLite — like a mini Swiggy for fish.

- **Entry point**: `artifacts/fish-delivery/app.py`
- **Templates**: `artifacts/fish-delivery/templates/`
- **Static**: `artifacts/fish-delivery/static/` (CSS, JS, image uploads)
- **Database**: `artifacts/fish-delivery/fish_delivery.db` (auto-created on first run)
- **Port**: 5000
- **Workflow**: "Start application" (`cd artifacts/fish-delivery && python3 app.py`)

### Roles & Demo Credentials
- **Admin**: admin@fish.com / admin123 — full access to all portals
- **Seller**: register at `/auth/register` with role=seller
- **Customer**: register at `/auth/register` with role=customer
- **Delivery Partner**: register at `/auth/register` with role=delivery

### Routes
- `/` — Landing page (stats, how-it-works, role cards)
- `/auth/login` — Unified login for all roles
- `/auth/register` — Register with role selector (seller/customer/delivery)
- `/auth/logout` — Logout
- `/seller` — Seller dashboard: fish listings, stats, revenue
- `/seller/add` — Add fish with image upload, price (INR), description
- `/seller/fish/toggle/<id>` — Toggle In Stock / Out of Stock
- `/seller/fish/delete/<id>` — Delete fish
- `/customer` — Browse fish with live search/filter
- `/customer/order/<id>` — Place order with auto-total calculator (INR)
- `/customer/confirm/<id>` — Order confirmation with ORD-XXXXX ID
- `/customer/orders` — Customer order history with status tracking
- `/delivery/orders` — Delivery partner's assigned orders (filter by status)
- `/delivery/orders/update/<id>` — Update delivery status
- `/delivery/admin` — Admin panel: all orders, stats, assign to partners, update status

### Template Structure
```
templates/
├── base.html           — Shared layout, role-aware navbar, flash toasts, loading overlay
├── index.html          — Landing page
├── auth/
│   ├── login.html
│   └── register.html   — Role selector (seller/customer/delivery)
├── seller/
│   ├── dashboard.html  — Fish listings table with stats
│   └── add_fish.html   — Add fish form with image preview
├── customer/
│   ├── browse.html     — Fish grid with live search
│   ├── order.html      — Order form with auto-total
│   ├── confirm.html    — Order confirmation with ORD-XXXXX
│   └── orders.html     — Order history
└── delivery/
    ├── my_orders.html  — Partner's orders with status update
    └── admin.html      — Admin all-orders table with assign + status dropdowns
```

### Static Assets
- `static/css/main.css` — Full design system (CSS variables, cards, badges, forms, responsive)
- `static/js/main.js` — Live search, auto-calculate total, toast dismissal, image preview, confirm-delete
- `static/uploads/` — Fish images (served by Flask static)

---

## Monorepo Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Structure

```text
artifacts-monorepo/
├── artifacts/
│   ├── api-server/         # Express API server (port 8080, /api)
│   └── fish-delivery/      # Flask fish delivery app (port 5000, /)
├── lib/                    # Shared libraries
│   ├── api-spec/           # OpenAPI spec + Orval codegen config
│   ├── api-client-react/   # Generated React Query hooks
│   ├── api-zod/            # Generated Zod schemas from OpenAPI
│   └── db/                 # Drizzle ORM schema + DB connection
├── pnpm-workspace.yaml
└── tsconfig.json
```

---
name: ecommerce-builder
description: Build a complete e-commerce store with product catalog, shopping cart, Stripe checkout, order management, and admin dashboard. Use when the user wants to sell products online, build a shop, create a store, add payments, or needs Stripe checkout integrated. Triggers on phrases like "build a store", "create an e-commerce site", "I want to sell products", "build a shop with Stripe", "create an online marketplace".
metadata:
  version: '1.0'
  category: build
  icon: 🛒
  color: '#10b981'
---

# E-Commerce Builder

## When to Use This Skill

Apply this skill when the user wants to sell products online:

- "Build me an online store for X"
- "Create an e-commerce site that sells Y"
- "I need a shop with Stripe checkout"
- "Build a marketplace for Z"
- Any request for a product catalog, store, shop, or commerce flow

## What This Skill Builds

A production-ready e-commerce application:

**Product Catalog**
- Product grid with search and category filters
- Product detail page (images, description, variants, stock)
- Featured products and new arrivals sections
- Product reviews and ratings
- Related products

**Shopping Cart**
- Persistent cart (localStorage + server sync for logged-in users)
- Cart sidebar/drawer with item management
- Quantity updates and item removal
- Cart total with tax calculation

**Checkout (Stripe)**
- Stripe Checkout session for secure payment
- Guest checkout (no account required)
- Order confirmation page with order number
- Email confirmation (order receipt)
- Stripe webhook for order fulfillment

**User Accounts**
- Register/login (optional for purchase)
- Order history with tracking status
- Saved addresses
- Wishlist

**Admin Dashboard**
- Product management (CRUD with image upload)
- Order management (view, update status, export)
- Inventory tracking with low-stock alerts
- Revenue dashboard (daily/monthly charts)
- Customer list

**Infrastructure**
- PostgreSQL: products, categories, orders, order_items, users, cart
- Image upload to S3/Cloudinary
- Stripe Checkout + webhook handler
- Email notifications (order placed, shipped, delivered)

## Instructions

1. **Define the catalog** — extract: product type, categories, whether digital or physical, inventory needed, variants (size/color)

2. **Build in 5 passes**:
   - Pass 1: Config + types + DB schema + Stripe setup
   - Pass 2: Product catalog (grid, filters, detail page)
   - Pass 3: Cart + checkout flow (Stripe)
   - Pass 4: User auth + order history + admin dashboard
   - Pass 5: Backend API + webhook + email templates + README

3. **Stripe rules**:
   - Use Stripe Checkout Sessions (not Elements) for simplicity
   - Webhook verifies payment before creating order
   - Never store card data

4. **Critical paths to test**:
   - Browse → add to cart → checkout → payment → order confirmation
   - Admin: add product → view orders → update status

5. **Code must include** complete Stripe integration with webhook handler

## Example Input → Output

Input: "Build an online store for handmade jewelry — categories for necklaces, earrings, bracelets. Each product has photos, price, and limited stock."

Output includes:
- `/src/pages/Shop.tsx` — product grid with category filter + search
- `/src/pages/Product.tsx` — product detail with add-to-cart
- `/src/components/Cart.tsx` — slide-out cart drawer
- `/src/pages/Checkout.tsx` — redirects to Stripe Checkout
- `/src/pages/OrderConfirmation.tsx` — thank you page
- `/server/routes/orders.ts` — create order + Stripe webhook
- `/database/schema.sql` — products, categories, orders, cart tables

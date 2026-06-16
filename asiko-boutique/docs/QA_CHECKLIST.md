# ASIKO BOUTIQUE — Manual QA Checklist

**Purpose**: Pre-launch and post-deployment verification for all ASIKO systems.
**Last Updated**: 2026-06-15
**Environment**: Production (Render) — `https://asiko-boutique.onrender.com`

---

## How to Use

1. Open the deployed site in your browser
2. Check each item below — mark ✅ PASS or ❌ FAIL
3. For failures, note the exact URL and what went wrong
4. Fix failures before launching marketing/promotions

---

## SECTION 1: STOREFRONT — HOMEPAGE

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 1.1 | Homepage loads | Visit `/` | Page renders, no 500 errors | |
| 1.2 | Hero section | Look at top of homepage | Dark emerald hero with tagline, floating PNG images | |
| 1.3 | Floating PNGs visible | Hero area | 3D fashion PNGs animate into view (bags, shoes, accessories) | |
| 1.4 | Category cards | Hero section | 8 category cards: Dress, Shirt, Trouser, Skirt, Jacket, Hoodie, Shoe, Bag | |
| 1.5 | Featured products | Scroll down | Product grid shows images, names in ₦, "Add to Cart" buttons | |
| 1.6 | Product images | Product cards | Images load (no broken image icons) | |
| 1.7 | Product prices | Product cards | All prices show ₦ (₦符号, not $) | |
| 1.8 | Add to Cart (no showroom) | Click "Add to Cart" on any product | Product added to cart, cart badge updates | |
| 1.9 | Trust badges | Below hero or above footer | Payment security, delivery, return policy badges visible | |
| 1.10 | Footer | Scroll to bottom | Dark emerald footer with newsletter, 4-column grid | |
| 1.11 | Newsletter signup | Enter email in footer, submit | Confirmation message appears | |
| 1.12 | Footer links | Footer columns | Home, Shop, Lookbook, FAQ, Contact, Shipping, Size Guide, Terms, Privacy | |
| 1.13 | Brand name | Header/logo | Shows "ASIKO Boutique" (or updated brand name) | |
| 1.14 | Brand tagline | Footer | Shows "Authentic Nigerian Fashion" (or updated tagline) | |
| 1.15 | Currency display | Throughout site | All prices use ₦ symbol | |

---

## SECTION 2: STOREFRONT — NAVIGATION

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 2.1 | Desktop nav links | Top navigation bar | Home, Shop, Lookbook, FAQ + any dynamic pages set to "show in nav" | |
| 2.2 | Mobile hamburger menu | Resize to mobile, tap hamburger | Slide-out menu with all nav links | |
| 2.3 | Dynamic pages in nav | Admin: set a custom page to "show in nav" | Page appears in both desktop and mobile nav | |
| 2.4 | Search overlay (⌘K) | Press Ctrl+K or Cmd+K | Search overlay opens with input field | |
| 2.5 | Search returns results | Type a product name in search | Matching products appear | |
| 2.6 | Search FAQ results | Type a question in search | FAQ entries appear | |
| 2.7 | Search AI fallback | Type something with no match | AI Stylist responds with fashion advice | |
| 2.8 | Search close | Press Escape or click X | Search overlay closes | |

---

## SECTION 3: STOREFRONT — PRODUCT PAGES

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 3.1 | Product detail page | Click any product | PDP loads with images, name, price, description, size/color selectors | |
| 3.2 | Product images | PDP | Multiple images viewable (if available) | |
| 3.3 | Size selector | PDP | Dropdown or buttons showing available sizes | |
| 3.4 | Color selector | PDP | Color options displayed | |
| 3.5 | Add to Cart from PDP | Select size + color, click "Add to Cart" | Product added, cart updates | |
| 3.6 | Variant selection | PDP | Correct price shown for selected variant | |
| 3.7 | Back to shop | Click "Back" or breadcrumb | Returns to shop page | |

---

## SECTION 4: CART & CHECKOUT

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 4.1 | Cart drawer opens | Click cart icon | Slide-out cart with items, quantities, total | |
| 4.2 | Cart badge count | Add 3 items | Badge shows "3" | |
| 4.3 | Update quantity | Change quantity in cart drawer | Price recalculates, badge updates | |
| 4.4 | Remove item | Click remove/delete on item | Item removed, total updates | |
| 4.5 | Empty cart | Remove all items | Cart shows "empty" message | |
| 4.6 | Proceed to checkout | Click "Checkout" | Redirects to `/checkout` | |
| 4.7 | Checkout form | Checkout page | Name, email, phone, address fields present | |
| 4.8 | Delivery options | Checkout page | Delivery method selection (pickup/delivery) | |
| 4.9 | Order summary | Checkout page | Items, quantities, subtotal, shipping, total in ₦ | |
| 4.10 | Place order | Fill form, click "Place Order" | Redirects to OPay payment page | |
| 4.11 | OPay payment page | OPay page | Card + bank transfer options visible | |
| 4.12 | Cancel payment | Click cancel on OPay | Returns to store with cancellation message | |

---

## SECTION 5: CUSTOMER ACCOUNT

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 5.1 | Register page | Visit `/register` | Form with name, email, phone, password, confirm password, terms checkbox | |
| 5.2 | Register — password visibility | Click eye icon on password field | Password toggles visible/hidden | |
| 5.3 | Register — confirm password | Enter mismatched passwords | Validation error shown | |
| 5.4 | Register — terms checkbox | Submit without checking terms | Validation error, cannot submit | |
| 5.5 | Register success | Fill all fields correctly | Account created, redirected to dashboard or login | |
| 5.6 | Login page | Visit `/login` | Email, password, remember me toggle, login button | |
| 5.7 | Login — password visibility | Click eye icon on password | Password toggles visible/hidden | |
| 5.8 | Login — remember me | Check "Remember me", login, close browser, reopen | Still logged in (session persists) | |
| 5.9 | Login success | Correct credentials | Redirects to customer dashboard | |
| 5.10 | Login failure | Wrong password | Error message, stays on login page | |
| 5.11 | Forgot password | Click "Forgot password?" link | Form to enter email appears | |
| 5.12 | Reset password email | Submit email on forgot-password page | Confirmation message (email sent to inbox) | |
| 5.13 | Reset password link | Click link in email | Password reset form loads | |
| 5.14 | Set new password | Enter new password on reset form | Password updated, redirected to login | |
| 5.15 | Customer dashboard | Login and visit `/account` | Dashboard with orders, profile, quick actions | |
| 5.16 | Dashboard quick actions | Dashboard page | 5 cards: My Orders, Profile, Wishlist, Support, Logout | |
| 5.17 | My Orders | Click "My Orders" | List of orders with status, dates, totals | |
| 5.18 | Order detail | Click an order | Full order details with items, status, timeline | |
| 5.19 | Profile page | Click "Profile" | Edit name, email, phone | |
| 5.20 | Logout | Click logout | Session cleared, redirected to homepage | |

---

## SECTION 6: ADMIN — AUTHENTICATION

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 6.1 | Admin login page | Visit `/admin/login` | Login form with email + password fields | |
| 6.2 | Default credentials | Login with `zerupth@gmail.com` / `zerupthcode` | Login succeeds, redirected to admin dashboard | |
| 6.3 | Wrong credentials | Enter wrong password | Error message, stays on login page | |
| 6.4 | Protected page without auth | Visit `/admin` directly | Redirected to `/admin/login` | |
| 6.5 | Admin logout | Click sidebar logout | Session cleared, redirected to `/admin/login` | |
| 6.6 | Brand name in sidebar | Admin sidebar | Shows "ASIKO Boutique" (or updated brand name) | |

---

## SECTION 7: ADMIN — DASHBOARD

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 7.1 | Dashboard loads | Login, visit dashboard | KPI cards: Total Sales, Total Orders, Products, Customers | |
| 7.2 | KPI values | Dashboard | Real numbers from database (not placeholder) | |
| 7.3 | Activity feed | Dashboard | Recent orders, reviews, new customers listed | |
| 7.4 | Notification bell badge | Login, check header | Bell shows dynamic unread count (red badge with number) | |
| 7.5 | Notification dropdown | Click bell icon | Dropdown shows 7 activity types: orders, customers, reviews, low stock, waitlist, emails, contacts | |
| 7.6 | Notification summary bar | Open dropdown | Top bar shows count per category (e.g. "2 orders 1 customers 0 reviews") | |
| 7.7 | Notification unread dot | Open dropdown | Items < 5 min old show blue dot, older items don't | |
| 7.8 | Mark all as read | Click "Mark read" in dropdown header | Unread badge disappears | |
| 7.9 | Mobile dropdown | Open bell on mobile | Dropdown is full-width with proper scroll, not clipped | |
| 7.10 | Empty notifications | No recent activity | Empty state with bell icon and "No notifications yet" message | |

---

## SECTION 8: ADMIN — PRODUCTS

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 8.1 | Products list | Click "Products" in sidebar | Table with all products, images, names, prices, stock | |
| 8.2 | Add product | Click "Add Product" | Form with name, description, category, price, images | |
| 8.3 | Product image upload | Add product, select image | Image preview shown, saved as base64 in DB | |
| 8.4 | Product categories | Add product | Category dropdown: Dress, Shirt, Trouser, Skirt, Jacket, Hoodie, Shoe, Bag | |
| 8.5 | Size variants | Add product | Add multiple sizes with prices | |
| 8.6 | Color variants | Add product | Add multiple colors | |
| 8.7 | Save product | Fill all fields, save | Product created, appears in list | |
| 8.8 | Edit product | Click edit on existing product | Form pre-filled with current values | |
| 8.9 | Save edits | Change price, save | Price updated | |
| 8.10 | Delete product | Click delete on product | Confirmation dialog (ASIKO-styled, not browser `confirm()`) | |
| 8.11 | Confirm delete | Confirm in dialog | Product removed from list | |
| 8.12 | Product appears on storefront | Visit `/` | Newly added product visible in featured section | |

---

## SECTION 9: ADMIN — ORDERS & SALES

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 9.1 | Sales section | Click "Sales" in sidebar | Order list with status, dates, totals | |
| 9.2 | Order statuses | Sales page | Filterable by: Pending, Confirmed, Shipped, Delivered, Cancelled | |
| 9.3 | Order detail | Click an order | Full details: items, customer info, payment status | |
| 9.4 | Update order status | Change status from Pending → Confirmed | Status saved, notification sent | |
| 9.5 | Operations section | Click "Operations" | Recent orders, low stock alerts, waitlist | |
| 9.6 | Low stock alerts | Operations | Products with stock ≤ 3 highlighted | |

---

## SECTION 10: ADMIN — SETTINGS

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 10.1 | Settings page | Click "Settings" in sidebar | All sections visible in sidebar | |
| 10.2 | Global Brand Settings | Section: Brand | Company name, tagline, footer text, currency symbol, currency code | |
| 10.3 | Save brand settings | Change brand name, save | Success toast appears ("Settings saved!") | |
| 10.4 | Brand propagation | Visit storefront after save | New brand name shows on all pages | |
| 10.5 | Per-section save | Go to any section, click save | Only that section saves, toast confirmation | |
| 10.6 | Page Configuration | Section: Page Configuration | Toggle visibility for Contact, FAQ, Shipping, Size Guide, AI Stylist, Lookbook | |
| 10.7 | Toggle a page off | Set FAQ to hidden, save | FAQ removed from nav and footer | |
| 10.8 | Toggle a page on | Set FAQ to visible, save | FAQ returns to nav and footer | |
| 10.9 | Email Settings | Section: Email/Brevo | Brevo API key, sender email, sender name, admin email | |
| 10.10 | Email Campaign Settings | Section: Email Campaigns | From name, reply-to, tracking toggle, unsubscribe link, footer text | |
| 10.11 | Notification Settings | Section: Notifications | Toggles for: New Order, Review, Low Stock — each controls notification visibility in bell dropdown | |
| 10.12 | Dark mode (admin) | Toggle dark mode in settings or sidebar | Admin switches to dark theme | |
| 10.13 | Dark mode persists | Reload admin page | Dark mode stays on | |
| 10.14 | Page reload stays on section | Scroll to a section, reload | Stays on same section (or at least same page, not redirected to dashboard) | |

---

## SECTION 11: ADMIN — EMAIL CENTER

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 11.1 | Email section | Click "Email" in sidebar | Email center loads with tabs | |
| 11.2 | Templates tab | Click Templates | List of email templates (Welcome, Order Confirmation, Shipping) | |
| 11.3 | Create template | Click Create | Form with name, subject, body (HTML), category | |
| 11.4 | Save template | Fill and save | Template created, appears in list | |
| 11.5 | Send test email | Click Send on a template | Form to enter recipient email | |
| 11.6 | Send email | Enter email, send | Success message (check inbox) | |
| 11.7 | Email logs tab | Click Logs | List of sent emails with status, recipient, date | |
| 11.8 | Email analytics tab | Click Analytics | Open rate, click rate stats | |

---

## SECTION 12: ADMIN — PAGES & BLOG

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 12.1 | Pages section | Click "Pages" in sidebar | List of custom pages | |
| 12.2 | Create page | Click Create | Form with title, slug, body HTML, type | |
| 12.3 | Save page | Fill and save | Page created | |
| 12.4 | Toggle "Go Live" | Set page to live | Page accessible on storefront at `/page/{slug}` | |
| 12.5 | Toggle "Show in Nav" | Set to show in nav | Page appears in storefront navbar | |
| 12.6 | Toggle "Show in Footer" | Set to show in footer | Page appears in footer links | |
| 12.7 | Blog section | Click Blog | List of blog posts | |
| 12.8 | Create blog post | Click Create | Form with title, content, excerpt, featured image | |
| 12.9 | Publish post | Save and publish | Post accessible at `/blog/{slug}` | |

---

## SECTION 13: ADMIN — AI STYLIST

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 13.1 | AI Stylist section | Click "AI Stylist" in sidebar | Training data list | |
| 13.2 | Training entries | AI Stylist page | 14 default entries (if seeded) | |
| 13.3 | Add training entry | Click Add | Form with category, question, answer | |
| 13.4 | Save entry | Fill and save | Entry added to list | |
| 13.5 | Edit entry | Click edit on entry | Form pre-filled | |
| 13.6 | Delete entry | Click delete | Confirmation dialog, entry removed | |

---

## SECTION 14: AI STYLIST — STOREFRONT

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 14.1 | Stylist page | Visit `/stylist` | Chat interface loads | |
| 14.2 | Chat with AI | Type "What should I wear to a wedding?" | Response with outfit suggestions | |
| 14.3 | Brand-aware response | Ask "What does ASIKO sell?" | AI knows ASIKO products and categories | |
| 14.4 | Product recommendations | Ask "Recommend a dress for a party" | Suggests specific ASIKO products | |
| 14.5 | Events tab | Click Events tab | List of Nigerian fashion events with SVG icons | |
| 14.6 | Event detail | Click an event | Event details with outfit suggestions | |
| 14.7 | Wardrobe tab | Click Wardrobe tab | User's wardrobe items (if logged in) | |
| 14.8 | Colors tab | Click Colors tab | Color analysis / color palette suggestions | |
| 14.9 | Chat UI — no footer | Scroll to bottom of chat page | No footer visible (full immersive chat) | |
| 14.10 | Tab icons (SVG) | Look at tab bar | SVG icons (not emoji/text) for Chat, For You, Events, Wardrobe, Colors | |

---

## SECTION 15: EMAIL SYSTEM

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 15.1 | Welcome email | Register a new customer | Welcome email arrives in inbox | |
| 15.2 | Order confirmation | Place an order | Confirmation email with order details arrives | |
| 15.3 | Shipping update | Admin marks order as shipped | Shipping email with tracking info arrives | |
| 15.4 | Password reset email | Click "Forgot Password" | Reset link email arrives | |
| 15.5 | Newsletter confirmation | Subscribe via footer | Confirmation email arrives | |
| 15.6 | Email branding | Open any email | ASIKO branding, correct sender name, ₦ currency | |
| 15.7 | Email deliverability | Check spam folder | Emails NOT in spam | |

---

## SECTION 16: DESIGN & BRANDING

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 16.1 | Dark mode (storefront) | Toggle storefront dark mode | Store switches to dark theme | |
| 16.2 | Dark mode (admin) | Toggle admin dark mode | Admin switches to dark theme | |
| 16.3 | Independent dark modes | Set admin to dark, storefront to light | Each maintains its own state | |
| 16.4 | Fashion-forward design | Browse storefront | Modern, stylish design (not generic e-commerce) | |
| 16.5 | Product cards "full of life" | Browse shop | Product cards have hover effects, good imagery | |
| 16.6 | 3D PNG images | Homepage hero, login, register, lookbook, footer | Real 3D-rendered PNGs visible | |
| 16.7 | No 3D showroom | Check navbar | No "Virtual Try-On" or "3D Showroom" link | |
| 16.8 | No broken images | Browse all pages | No broken image icons | |

---

## SECTION 17: MOBILE RESPONSIVENESS

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 17.1 | Homepage mobile | Resize to 375px width | Layout adjusts, no horizontal scroll | |
| 17.2 | Product cards mobile | Shop page on mobile | Cards stack vertically, readable | |
| 17.3 | Cart mobile | Cart drawer on mobile | Full-width, usable | |
| 17.4 | Checkout mobile | Checkout form on mobile | Fields stack, easy to fill | |
| 17.5 | Admin sidebar mobile | Admin on mobile | Sidebar hidden, hamburger menu works | |
| 17.6 | Admin dashboard mobile | Dashboard on mobile | KPI cards stack, content readable | |
| 17.7 | Customer dashboard mobile | Account page on mobile | Quick actions stack, readable | |
| 17.8 | Login/Register mobile | Auth pages on mobile | Forms centered, no bleed | |
| 17.9 | AI Stylist mobile | `/stylist` on mobile | Chat interface usable, tabs accessible | |
| 17.10 | Customer dashboard background | Account page on mobile | No white bleed at bottom | |

---

## SECTION 18: PERFORMANCE & TECHNICAL

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 18.1 | Page load time | Homepage | Loads in < 3 seconds | |
| 18.2 | DB connection | First visit after idle | No timeout errors (retry logic works) | |
| 18.3 | Static assets | CSS, JS, images | All load correctly | |
| 18.4 | No console errors | Open browser DevTools | No JavaScript errors in console | |
| 18.5 | HTTPS | Check URL bar | Secure connection (padlock icon) | |
| 18.6 | Favicon | Browser tab | ASIKO favicon visible | |

---

## SECTION 19: CONTENT PAGES

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 19.1 | FAQ page | Visit `/faq` | Category filter pills, 11 Q&As | |
| 19.2 | FAQ filtering | Click a category pill | Only FAQ items in that category shown | |
| 19.3 | Contact page | Visit `/contact` | Form (name, email, subject, message) + address/phone cards | |
| 19.4 | Submit contact form | Fill and submit contact form | Success message, message saved to DB | |
| 19.5 | Shipping page | Visit `/shipping` | Delivery zones, shipping rates, returns policy | |
| 19.6 | Size Guide page | Visit `/size-guide` | Measurement tables with tabs (Women's, Men's, How to Measure) | |
| 19.7 | About page | Visit `/about` | Brand story, mission, values, team, Instagram section | |
| 19.8 | Terms page | Visit `/terms` | Terms of Service, 9 sections | |
| 19.9 | Privacy page | Visit `/privacy` | Privacy Policy, 10 sections | |

---

## SECTION 20: SEARCH

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 20.1 | Open search | Press Ctrl+K / Cmd+K | Search overlay opens | |
| 20.2 | Product search | Search for a product name | Matching products listed | |
| 20.3 | FAQ search | Search for a question | FAQ entries listed | |
| 20.4 | Blog search | Search for a blog title | Blog posts listed | |
| 20.5 | AI fallback | Search for something with no match | AI Stylist responds with advice | |
| 20.6 | Search close | Press Escape | Overlay closes | |
| 20.7 | Search from mobile | Open search on mobile | Overlay usable on small screen | |

---

## CRITICAL FAILURES (Launch Blockers)

These MUST pass before going live:

| # | Critical Test | Status |
|---|---------------|--------|
| C1 | Homepage loads without errors | |
| C2 | Products display with ₦ prices and images | |
| C3 | Add to Cart works without showroom | |
| C4 | Checkout → OPay payment flow completes | |
| C5 | Customer registration + login works | |
| C6 | Admin login with default credentials works | |
| C7 | Admin can add/edit/delete products | |
| C8 | Admin settings save with toast confirmation | |
| C9 | Brand settings propagate to all pages | |
| C10 | Emails send (welcome, order confirmation) | |
| C11 | Mobile responsiveness on all key pages | |
| C12 | No 500 errors on any page | |

---

## QUICK SMOKE TEST (5 minutes)

Run this abbreviated check before every deployment:

1. Visit `/` — loads? ✅
2. Click a product — PDP loads? ✅
3. Add to cart — badge updates? ✅
4. Visit `/admin/login` — login works? ✅
5. Dashboard loads with real KPIs? ✅
6. Settings save without error? ✅
7. Visit `/stylist` — AI chat responds? ✅
8. Visit `/faq` — FAQ loads? ✅
9. Visit `/` on mobile — no white bleed? ✅
10. No console errors? ✅

---

## NOTES

- **OPay is in mock mode** — payments won't actually process until production keys are set
- **Brevo is live** — test emails will send to real inboxes
- **Database is live** — Neon Postgres on Render
- **Brand settings** default to: "ASIKO Boutique", "Authentic Nigerian Fashion", ₦ symbol, NGN code
- **Admin default login**: `zerupth@gmail.com` / `zerupthcode`
- **AI Stylist** uses OpenRouter free models — may have rate limits during heavy testing

---

*Document maintained by Claude Code. Update after each deployment.*

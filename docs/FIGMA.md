# AJORA – Figma handoff for VS Code (Claude Code)

Figma file: "AJORA – Design" · https://www.figma.com/design/M95uPMv61dMZF0YLEU2DJV
Design finished 22 Nov 2026. Coding starts 24 Nov (C1). Read frames with `get_design_context` using the node IDs below, then rebuild them with our own Flask + Jinja2 + HTML/CSS/JS. Never paste generated code as it is.

## Pages
| Page | Contents |
|---|---|
| 00 · Logo & icons | Logo set (Positive 5:212, Reversed 5:217, On Emerald 5:222, One colour 5:227), app icon 5:233, favicon 5:237, 52 icons (frame 3:112) |
| 01 · Design system | Variables, 15 text styles, 4 effect styles, 32 components, Foundations 15:827, Component overview 16:827 |
| 02 · Public screens | Screens 1–3 · 12 frames |
| 03 · Customer screens | Screens 4–11 + pop-up 1 · 39 frames |
| 04 · Admin screens | Screens 12–20 + pop-ups 2–7 · 51 frames |
| 05 · Prototype | Handoff and prototype guide (52:279) |

Total 102 frames: 20 screens × 3 sizes, 7 pop-ups × 2 sizes, plus loading, empty, error and special states.

## Screen index (node IDs)
| Screen | Laptop 1440 | Tablet 834 | Mobile 390 | States |
|---|---|---|---|---|
| 1 Landing | 18:279 | 18:676 | 18:1021 | |
| 2 Log in | 19:897 | 19:966 | 19:1015 | wrong password 19:1063 · locked 19:1125 |
| 3 Create account | 19:1183 | 19:1295 | 19:1393 | email taken 19:1490 |
| 4 Customer home | 23:280 | 23:502 | 24:548 | first order 24:760 · loading 24:929 |
| 5 Order fuel | 25:770 | 25:966 | 26:933 | location off + errors 26:1109 |
| 6 Emergency fuel | 27:1076 | 27:1193 | 27:1326 | already open 27:1439 |
| 7 Generator & machinery | 28:1259 | 28:1495 | 28:1743 | |
| 8 Vehicle assistance | 33:1867 | 33:2094 | 33:2381 | car wash too soon 33:2578 |
| 9 Order confirmed | 34:2211 | 34:2331 | 34:2464 | searching 34:2577 · scheduled + call 34:2677 |
| 10 Track order | 35:2446 | 35:2625 | 35:2845 | delivered 35:3045 · cancelled 35:3233 |
| 11 My orders | 36:2872 | 36:3273 | 36:3674 | empty 36:3970 |
| 12 Admin dashboard | 38:280 | 38:782 | 38:1124 | |
| 13 All orders | 39:714 | 39:1619 | 40:1495 | no match 40:1868 · filters sheet 40:1942 |
| 14 Order details | 41:1797 | 41:2145 | 41:2376 | emergency 41:2576 · call needed 41:2718 · delivered 41:2855 |
| 15 Emergency requests | 44:2614 | 44:2945 | 44:3122 | none open 44:3275 |
| 16 Customers | 45:2913 | 45:3585 | 45:4021 | |
| 17 Services and prices | 46:3411 | 46:3876 | 46:4143 | |
| 18 Drivers | 47:4092 | 47:4701 | 47:4982 | |
| 19 Reports | 48:4801 | 48:5195 | 48:5442 | empty period 48:5668 |
| 20 Error page | 49:5166 (404) | 49:5198 (500) | 49:5226 (403) | 429 49:5247 · 400 49:5268 |
| P1 Confirm order | 29:1530 | — | 29:1639 | placing 29:1709 · price updated 29:1790 · emergency 29:1875 |
| P2 Assign / change driver | 42:2169 | — | 42:2368 | no driver free 42:2531 |
| P3 Update status / cancel | 42:2659 | — | 42:2814 | |
| P4 Customer panel | 45:4195 | — | 45:4714 | |
| P5 Add / edit service | 46:4352 | — | 46:4612 | turn off confirm 46:4788 |
| P6 Add / edit driver | 47:5127 | — | 47:5512 | remove refused 47:5720 |
| P7 Log out | 49:5290 | — | 49:5513 | |

## Rules for the code
- Tokens: every colour, spacing and radius is a Figma variable with WEB code syntax, e.g. `var(--color-bg-surface)`, `var(--color-text-primary)`, `var(--space-lg)`, `var(--radius-md)`. Put them all in `static/css/tokens.css`.
- Text styles become CSS classes: `.display`, `.h2`, `.h3`, `.h4`, `.body-lg`, `.body`, `.body-strong`, `.label`, `.label-sm`, `.caption`, `.overline`, `.mono-amount`, `.mono-stat`. Inter and JetBrains Mono are self-hosted.
- Breakpoints: mobile up to 599 px (design 390), tablet 600–1023 (design 834), laptop 1024+ (design 1440, content max 1200).
- Customer navigation: bottom tabs on mobile and tablet; tabs in the top bar from 1024 px. Form screens (5–8) on mobile use the fixed Action bar instead of the bottom tabs.
- Admin navigation: 240 px sidebar on laptop, 72 px icon rail on tablet, menu button + top bar on mobile.
- Components become Jinja macros in `templates/components/` (button, icon button, field, chip, segmented control, stepper, switch, status chip, service tile, emergency card, stat card, driver card, alert banner, toast, empty state, skeleton, status steps, pagination, table row, dialog/sheet, action bar).
- Icons: Font Awesome Free 6 Solid as inline SVG (plus the custom tyre icon).
- Formats: money `PKR 5,040` in mono font · dates `05 Oct 2026, 7:40 pm` · orders `ORD-0042` · phones `0300-1234567`.
- Pop-ups: bottom sheet on mobile, centred dialog 440–560 px on tablet and laptop, side panel 420 px for the customer panel. Focus stays inside, Esc closes, focus returns to the button that opened it.
- Error page: plain words only, never a code or stack trace, always a button back to safety.

## Seed data used in the designs (match it in the database seed)
- Prices: Petrol PKR 252/L, Diesel PKR 258/L, Engine oil 2,800, Battery help 1,500, Tyre help 600, Car wash 1,000 per service.
- Customer Ali Raza (0300-1234567, ali.raza@example.com): ORD-0042 Petrol 20 L PKR 5,040 on the way (driver Ahmed Raza, LEA-1234); ORD-0043 Generator 250 L PKR 64,500, call needed; 23 orders.
- Open emergencies: ORD-0046 Sana Iqbal 10 L (6 min), ORD-0047 Bilal Khan 5 L (4 min).
- Drivers: Ahmed Raza (Busy), Bilal Ahmed LEA-5521, Usman Ali, Kashif Iqbal, Faisal Mehmood, Naveed Akhtar, Shahid Butt, Tariq Javed, Adnan Raza (Off duty). Admin: Sana Ahmed.
- Reports week 16–22 Nov: 300 counted (281 delivered, 19 cancelled, 27 emergency), PKR 1,284,600, average 24 min.

## Prototype flows (press Play in Figma)
- 02 · Public: "Public · Laptop", "Public · Mobile (with security states)".
- 03 · Customer: "Customer · Mobile", "Customer · Laptop" (Placing order moves on after 1.2 s; Track order becomes Delivered after 5 s).
- 04 · Admin: "Admin · Laptop" (sidebar on every page, order details, driver and status pop-ups, customer panel, service edit, driver add/remove).

## Known limits of the Figma prototype
- Links only work inside one page, so each page has its own flows.
- Generator and Vehicle "Review order" open the petrol confirm sheet; in code pop-up 1 shows the real service.
- Charts are drawn shapes; in code they use Chart.js (self-hosted).
- The phone picture on the mobile Landing is scaled down on purpose (text under 10 px).
- Live parts (30 s customer polling, 15 s admin refresh, toasts, timers) are shown as states; the code adds the timers.

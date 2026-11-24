# AJORA – screens and flows (exact spec)

Source: the "Screens and flows" tab of the AJORA plan. Words in quotes are the exact UI text. Node IDs for each screen are in docs/FIGMA.md. Version 1 note: customers do not cancel orders; only the admin cancels (with a reason).

Every screen of AJORA, how it reacts to each tap, and which screen comes next. Claude uses this tab as the exact spec in Figma and in VS Code.

## Navigation map
Create account always leads to Customer home; Log in sends each user to the dashboard of their role. An admin status change reaches the customer's Track order page within 30 seconds.

## Rules for every screen
These rules apply everywhere, so each screen below lists only what is special about it.

### Layout and navigation
- Public pages: top bar with AJORA logo, "How it works", "Services", "Log in" (outline button) and "Create account" (brand button). On mobile the links fold into a menu button.
- Customer pages (mobile-first): top bar with logo and a log out icon; bottom navigation with 3 tabs: Home, Track (greyed out when there is no active order), My orders. From 1024 px wide the bottom tabs move into the top bar and forms sit in a centred 720 px column.
- Admin pages (desktop-first): left sidebar 240 px: Dashboard, Orders, Emergency (red count badge), Customers, Services, Drivers, Reports, then admin name and Log out at the bottom. Below 1024 px the sidebar shrinks to icons; below 768 px it opens from a menu button.
- The current tab or menu item is marked in Emerald with an icon and bold text, never colour alone.

### Feedback after every action

| Moment | What the user sees | Timing |
| --- | --- | --- |
| Button pressed | Button shrinks to 97% and back | 120 ms |
| Saving | Button disabled, small spinner, text changes ("Placing order…") so it cannot be pressed twice | Until server answers |
| Success | Toast with check icon (mobile: top centre, desktop: bottom right), also read out by screen readers | Stays 4 s |
| Field error | Red text with icon under the field, red border, focus jumps to the first wrong field | Instantly |
| Server or internet problem | Banner "Check your internet and try again" with a Retry button; typed data is kept | Until fixed |
| Page change | Content fades in | 200 ms |
| Pop-up | Mobile: sheet slides up from the bottom. Desktop: centred dialog with dark backdrop | 250 ms |

### States no screen may miss
- Loading: grey skeleton blocks in the shape of the content if loading takes over 300 ms. No full-screen spinner.
- Empty: icon, one plain line and the main action ("No orders yet" + "Order fuel").
- Error: plain words that say what to do next, never a code or stack trace.
- Session expired: after 30 minutes idle the next click goes to Log in with "You were logged out after 30 minutes of no activity", and after logging in the user returns to the same page.

### Formats and accessibility
- Money: PKR 5,040 (mono font). Dates: 05 Oct 2026, 7:40 pm. Order numbers: ORD-0042. Phones: 0300-1234567.
- Tap targets at least 44 × 44 px; every input has a visible label; everything works with the keyboard; "reduce motion" turns off slides and fades.
- No looping or pulsing animations (brand rule); the only special animation is the success check on Order confirmed, played once (500 ms).

## Layouts by device
Every screen has a fixed layout for 3 sizes, so it looks designed on each device, not just squeezed. On tablet and laptop the main action of each screen is visible without scrolling; on mobile it sits in a fixed bar at the bottom.

| Device | Figma frame | CSS range | Also tested at |
| --- | --- | --- | --- |
| Mobile | 390 × 844 | up to 599 px | 360 px |
| Tablet | 834 × 1194 | 600 to 1023 px | 768 px and 1024 px landscape |
| Laptop | 1440 × 900 | 1024 px and up (content max 1200 px) | 1280 px and 1920 px |

### Less-scrolling rules
- Order forms: on tablet and laptop, 2 columns — form on the left, a sticky summary on the right with the total and the Review button. On mobile, one column with a fixed bottom bar holding the total and the button.
- Fewer taps: chips and switches instead of dropdowns when there are 5 options or fewer; optional fields stay folded ("Add a note").
- Admin lists: sticky table header, 20 rows per page with page numbers, all filters in one row on laptop (a "Filters" button on tablet and mobile).
- Dashboards: the admin dashboard fits a 1440 × 900 laptop screen with no page scroll; the customer home fits too.
- Tables on mobile turn into cards, so there is never sideways scrolling.
- Landing page: only 6 sections; the hero with both main buttons fits the first screen on every device.

### Screen-by-screen layout

| Screen | Mobile | Tablet | Laptop |
| --- | --- | --- | --- |
| 1 Landing | Stacked hero, phone image under the buttons, service tiles 2 per row | Hero text left, phone right; tiles 3 per row | Hero in 2 columns; tiles 4 per row; How it works 3 in a row |
| 2 Log in | Full-width form card | Centred 480 px card | Split screen: Obsidian brand panel left, form right |
| 3 Create account | Full-width form | Centred 560 px card | Split screen; name, email, phone in 2 columns |
| 4 Customer home | Active order card, Emergency button, tiles 2 per row, bottom nav | Active order and Emergency side by side; tiles 3 per row | Left: active order + Emergency; right: tiles 4 per row; fits one screen |
| 5 Order fuel | One column, fixed bottom bar (total + Review order) | Form left, sticky summary right | Same as tablet, wider; whole form fits one screen |
| 6 Emergency fuel | Location status on top, chips, big red button fixed at bottom | Centred 560 px card, all in one screen | Same as tablet |
| 7 Generator and machinery | Like screen 5; time slots as a chip grid | Form left, sticky summary right | Same as tablet |
| 8 Vehicle assistance | Service cards 2 per row, then form, fixed bottom bar | Service cards in one row of 4; form + summary below | Same as tablet, wider |
| 9 Order confirmed | Check, order number, driver card; buttons fixed at bottom | Centred card: summary left, driver right | Same as tablet |
| 10 Track order | ETA, status steps and driver card in the first screen; summary folded | Steps left, driver + summary right | Same as tablet, wider |
| 11 My orders | Order cards, filter chips, page numbers | Table with filter chips and page numbers | Same as tablet, all columns |
| 12 Admin dashboard | Cards 2 × 2, emergency bar, lists stacked | Icon sidebar, cards 2 × 2, lists stacked | Full sidebar, 4 cards in a row, latest orders left, Due soon / Call needed / Security right; fits one screen |
| 13 All orders | "Filters" sheet, orders as cards | Icon sidebar, table without Area and Time columns | Full table, one-row filters, sticky header |
| 14 Order details | Stacked sections, status buttons in fixed bottom bar | 2 columns | Info 60% left, driver + status + history 40% right |
| 15 Emergency requests | Cards stacked | Cards 2 per row | Cards 3 per row |
| 16 Customers | Search + cards; panel opens full screen | Table; panel slides in at 420 px | Same as tablet |
| 17 Services | Cards with on/off switch | Table | Table |
| 18 Drivers | Cards with status chip | Table | Table |
| 19 Reports | Period switch, cards 2 per row, charts full width | Cards 3 per row, 1 chart per row | 6 cards in a row, 2 charts per row |
| 20 Error page | Centred message and button | Same | Same |
| Pop-ups | Bottom sheet up to 90% height | Centred dialog 480–560 px | Same as tablet |

## Route map
Every URL of the website is listed here; anything not on this list returns the 404 page. Rule: GET only shows data; every change uses POST with a CSRF token.

| URL | Method | Who can open | What it does |
| --- | --- | --- | --- |
| / | GET | Everyone | Landing page |
| /login | GET, POST | Logged-out users | Log in; logged-in users are sent to their dashboard |
| /register | GET, POST | Logged-out users | Create a customer account |
| /logout | POST | Logged-in users | Ends the session, back to landing |
| /app | GET | Customer | Customer home |
| /app/order/fuel | GET, POST | Customer | Order petrol or diesel |
| /app/order/emergency | GET, POST | Customer | Emergency fuel |
| /app/order/generator | GET, POST | Customer | Generator and machinery fuel |
| /app/order/assistance | GET, POST | Customer | Engine oil, battery, tyre, car wash |
| /app/orders | GET | Customer | Order history (?page=2&show=active) |
| /app/orders/<id>/confirmed | GET | Owner of the order | Order confirmed |
| /app/orders/<id> | GET | Owner of the order | Track order / finished order details |
| /app/orders/<id>/repeat | GET | Owner of the order | Opens the right form filled with the old order |
| /api/orders/<id>/status | GET | Owner or admin | JSON for tracking: status, driver, ETA |
| /admin | GET | Admin | Dashboard |
| /admin/orders | GET | Admin | All orders with filters in the URL |
| /admin/orders/<id> | GET | Admin | Order details |
| /admin/orders/<id>/assign | POST | Admin | Assign or change driver |
| /admin/orders/<id>/status | POST | Admin | Move status forward, back to Pending, or cancel |
| /admin/orders/<id>/call-done | POST | Admin | Mark the 200+ litre call as done |
| /admin/emergency | GET | Admin | Open emergency requests |
| /admin/customers | GET | Admin | Customer list with search |
| /admin/customers/<id> | GET | Admin | Customer side panel |
| /admin/customers/<id>/block | POST | Admin | Block or unblock |
| /admin/services | GET, POST | Admin | List and add services |
| /admin/services/<id> | POST | Admin | Edit, turn on or off |
| /admin/drivers | GET, POST | Admin | List and add drivers |
| /admin/drivers/<id> | POST | Admin | Edit, change status |
| /admin/drivers/<id>/remove | POST | Admin | Remove (refused while the driver has an active order) |
| /admin/reports | GET | Admin | Reports (?period=week&date=2026-11-30) |
| /api/admin/live | GET | Admin | JSON: live counts and new emergencies |

## Public screens (1–3)

### 1. Landing page
- Opens from: typing the address, tapping the logo, or after log out.
- Shows, top to bottom:
- Hero: headline "Fuel and road help, brought to you.", one line under it, buttons "Order fuel" (brand) and "Emergency fuel" (red outline), and a real Track order screen inside a phone frame.
- Services: 7 tiles (Petrol and diesel, Emergency fuel, Generator fuel, Machinery fuel, Engine oil, Battery and tyre help, Car wash).
- How it works: 3 steps — Choose a service → Share your location → Track your driver.
- Why AJORA: one platform, emergencies first, nearest driver, price before you order.
- Who it is for: daily commuters, homes and shops with generators, farmers.
- Closing call to action and footer (© 2026 AJORA · Final Year Project, University of Lahore).
- Reactions:
- "Order fuel", "Emergency fuel" or any service tile → logged out: Log in page with "Log in to place your order", and after login the user lands on that exact order page. Logged-in customer: straight to that order page.
- Top links scroll smoothly to their section (instant jump when reduce motion is on). The top bar gets a thin bottom border once the page scrolls.
- A logged-in admin sees "Open dashboard" instead of the order buttons.

### 2. Log in
- Shows: Email, Password with a show / hide eye button, "Log in" button, link "New to AJORA? Create account".
- Reactions:
- Enter key submits. Button changes to "Logging in…".
- Success: customer → Customer home (or the page they wanted); admin → Admin dashboard. Toast "Welcome back, Ali".
- Already logged in and opening /login → sent to their own dashboard.
- Errors (exact words):
- Empty field: "Enter your email" / "Enter your password".
- Wrong email or password: "Email or password is not correct." (never says which one, so attackers cannot find real emails).
- 5 wrong tries: "Too many tries. Try again in 10 minutes." with the minutes left.
- Blocked account (shown only after the correct password): "This account is blocked. Please contact AJORA support."
- Not in version 1: forgot password (not in the document); a small line says "Forgot your password? Contact AJORA support."

### 3. Create account
- Shows: Full name, Email, Phone (hint 03XX-XXXXXXX), Password, Confirm password, a short privacy line ("Your location is used only for your own orders"), "Create account" button, link "Already have an account? Log in".
- Reactions:
- Each field is checked when the user leaves it; the password shows a 3-tick list: at least 8 characters, not a common password, not the same as your email.
- Phone is shown as 0300-1234567 while typing and saved as 03001234567.
- Success: the user is logged in at once and lands on Customer home with "Account created. Welcome to AJORA."
- Errors: "Enter your full name", "Enter a valid email", "Enter a valid mobile number like 0300-1234567", "Passwords do not match", "This email is already registered. Log in instead?" (with link), "This phone number is already registered."

## Customer screens (4–11)
A normal order takes 4 taps after the form is filled: choose service → fill form → Review order → Confirm order (NFR-03 allows 5).

### 4. Customer home
- Opens from: login, bottom tab Home, "Back to home" buttons.
- Shows: "Assalam-o-Alaikum, Ali"; active order card (service, status chip, "Arriving in about 12 min", "Track order") when one exists; full-width red Emergency fuel button; 2-column service tiles with the price per unit; last finished order with "Order again".
- Only services turned on by the admin appear (FR-14).
- Reactions:
- Petrol and diesel → screen 5. Generator fuel or Machinery fuel → screen 7 with that type already picked. Engine oil, Battery, Tyre, Car wash → screen 8 with that service picked.
- Emergency fuel → screen 6. If an emergency is already open → its Track page with "You already have an open emergency request".
- The active order card refreshes itself every 30 seconds.

### 5. Order fuel (FR-03)
- Fuel type: Petrol | Diesel switch, each showing its price per litre from the database.
- Litres: minus / plus buttons (steps of 5), typed number, quick chips 10, 20, 50. Allowed 5 to 100.
- Live total: "PKR 5,040" changes the moment litres or fuel type change.
- Location card: "Use my current location" → browser asks permission →
- allowed: "Location captured" with a check and accuracy ("within 30 m");
- blocked: "Location is off. Pick your area and type your address." and the Area list is highlighted.
- Address (required, up to 200 characters), Landmark / note (optional, "near Shell pump gate"), Area list (required when location is off).
- Reactions: "Review order" → checks every field → opens pop-up 1. If the admin changed the price meanwhile, pop-up 1 shows "Price updated to PKR 255 per litre" and the new total.
- Errors: "Enter between 5 and 100 litres", "Add your address so the driver can find you", "Pick your area".

### 6. Emergency fuel (FR-04)
- Opens with a short line "We need your location to send the nearest driver" and asks for location at once.
- Shows: fuel type, litres chips 2, 5, 10 (maximum 10), vehicle note ("White Corolla near exit 4"), the phone the driver will call.
- Reactions: big red "Send emergency request" → short red confirm sheet (pop-up 1) → screen 9 with a red Emergency badge. The order goes to the top of the queue.
- Errors: "Emergency orders are limited to 10 litres", "You already have an open emergency request" (with "Track it" link).

### 7. Generator and machinery fuel (FR-05)
- Shows: type (Generator | Tractor or harvester | Tube well), fuel type, litres 20 to 500 with live total, site address, area, optional location, delivery time: "As soon as possible" or a day (next 7 days) and a 2-hour slot between 8 am and 8 pm.
- Reactions: above 200 litres an info box appears at once: "For more than 200 litres our team will call you to confirm before the driver leaves." Review → pop-up 1 → screen 9.
- After placing: "As soon as possible" orders go to smart dispatch at once; above 200 litres they wait until the admin marks the call done; scheduled orders are dispatched by the admin from the "Due soon" list.

### 8. Vehicle assistance (FR-06)
- Shows: 4 service cards with price (Engine oil delivery, Battery help, Tyre help, Car wash), vehicle type (Motorcycle, Car, Rickshaw, Van or pickup), time, address, area, location.
- Time rules: Battery and Tyre default to "Now"; Car wash cannot be "Now" — the earliest slot shown is 2 hours from now, and the server checks again.
- Reactions: Review → pop-up 1 → screen 9.
- Errors: "Car wash must be booked at least 2 hours ahead".

### 9. Order confirmed
- Shows: check animation (once), order number ORD-0042, service and quantity, total, "Cash on delivery", address.
- Driver found: driver card — name, rating, vehicle number, "4.2 km away", "Arriving in about 13 min", Call button (opens the phone dialler).
- No driver yet: amber card "Searching for a driver. We will assign one shortly." The page checks every 30 seconds and swaps to the driver card when assigned.
- Scheduled / call needed: "Scheduled for 21 Nov, 4–6 pm" or "Our team will call you shortly to confirm".
- Buttons: "Track order" → screen 10; "Back to home" → screen 4.
- Refreshing this page never creates a second order (the order was saved before the redirect).

### 10. Track order (FR-07)
- Shows: status steps Placed → Assigned → On the way → Delivered with the time of each; driver card with Call; ETA line updated every minute ("Arriving in about 9 min", then "Arriving any moment"); order summary that opens on tap.
- Reactions:
- The page asks the server every 30 seconds. When the status changes, the next step lights up (250 ms) and a toast says "Your driver is on the way".
- Delivered: "Delivered at 7:52 pm", checking stops, "Order again" appears.
- Cancelled: red card with the reason, checking stops.
- While the browser tab is hidden the checks pause, and they restart when the user returns (saves data).

### 11. My orders (FR-08)
- Shows: filter chips All | Active | Delivered | Cancelled; list newest first, 10 per page with page numbers; each row: date, service icon and name, quantity, amount, status chip.
- Reactions: tap a row → screen 10 (live for active orders, read-only for finished ones). "Order again" → the right form already filled with service, quantity, address and area; location is asked again.
- Empty: "No orders yet" + "Order fuel".

## Admin screens (12–19) and error page (20)
Admin pages refresh their live parts every 15 seconds through /api/admin/live, so the admin never has to reload. The browser tab title shows open emergencies, e.g. "(2) AJORA Admin".

### 12. Admin dashboard (FR-09, FR-12)
- Shows: 4 cards for today — Orders, Open emergencies, Sales (delivered, PKR), Free drivers ("5 of 8"); red emergency bar when any emergency is open ("2 emergency requests waiting · oldest 3 min"); "Due soon" list (scheduled within 60 minutes); "Call needed" list (orders above 200 litres); latest 10 orders; small Security card (today's failed logins and lockouts, red when an account is locked).
- Reactions: emergency bar → screen 15; any order row → screen 14; new orders slide into the table with a soft highlight that fades once.

### 13. All orders (FR-09)
- Filters: status (several at once), service, date (Today, 7 days, 30 days, custom), "Emergency only" switch, search by order number or phone. Filters live in the URL, so refresh and the back button keep them.
- Table: Order, Customer, Service, Quantity, Amount, Area, Status, Driver, Time; 20 rows per page.
- Rule: open emergency rows always sit on top with a red left border and icon (FR-09 business rule).
- Empty: "No orders match these filters" + "Clear filters".

### 14. Order details (FR-10, FR-11)
- Left side: order info, customer name and phone (Call), address, landmark, area, coordinates with a copy button, note, delivery time, amount; badges "Emergency" or "Call needed" with a "Mark call done" button.
- Right side: driver card or "Not assigned" with "Assign driver" / "Change driver" (pop-up 2); route list when the driver has more than one stop ("Stop 2 of 3").
- Status buttons show only the allowed next moves:

| Current status | Buttons shown |
| --- | --- |
| Pending | Assign driver · Cancel order |
| Assigned | Mark on the way · Back to pending · Cancel order |
| On the way | Mark delivered |
| Delivered or Cancelled | None (read-only) |

- Each button opens pop-up 3. After saving, the tracking history list (time + status) gains a row, and the customer's page shows it within 30 seconds.
- Driver updates itself: assigned → Busy; delivered or cancelled → Available again, and on delivery the driver's last known location becomes the customer's location (keeps dispatch distances realistic without a driver app).

### 15. Emergency requests (FR-12)
- Shows: one card per open emergency, oldest first: waiting timer ("6 min"), customer and Call button, area and address, fuel and litres, vehicle note, status, driver.
- 5-minute rule: an unassigned request older than 5 minutes gets a thick red border and the label "Waiting over 5 min", and moves to the top.
- Reactions: Assign driver → pop-up 2; Open → screen 14.
- Empty: green check and "No open emergencies".

### 16. Customers (FR-13)
- Shows: search by name, email or phone (results update 300 ms after typing stops); table Name, Phone, Email, Orders, Last order, Status (Active / Blocked); 20 per page.
- Reactions: row → pop-up 4 side panel.

### 17. Services and prices (FR-14)
- Shows: reminder bar "Fuel prices must match the latest government rate"; table Service, Category, Unit, Price (PKR), Available switch, Edit.
- Reactions: "Add service" or Edit → pop-up 5. Turning a service off asks "Customers will not see Tyre help. Turn it off?" and hides it from customers at once.

### 18. Drivers (FR-15)
- Shows: table Name, Phone, Vehicle number, Area, Status chip (Available / Busy / Off duty), Open orders, Rating.
- Reactions: quick switch Available ↔ Off duty (Busy is set only by the system); "Add driver" or Edit → pop-up 6; Remove → confirm, refused when busy: "Ahmed has an active order. Finish or reassign it first."

### 19. Reports (FR-16)
- Shows: Day | Week | Month switch with previous / next arrows; cards Total orders, Delivered, Cancelled, Emergency, Sales (PKR), Average delivery time (min); charts: orders per day (bars), orders by service (horizontal bars), predicted vs actual delivery time.
- Rule: only Delivered and Cancelled orders in the chosen dates are counted, and a small note under the cards says so.
- Empty: zero values + "No completed orders in this period".

### 20. Error page
One page, different message per case, always with a button back to safety:

| Case | Message |
| --- | --- |
| 404 | We could not find this page. |
| 403 | This page is for AJORA admins only. |
| 400 (expired form) | This form expired. Reload the page and try again. |
| 429 | Too many tries. Wait a minute and try again. |
| 500 | Something went wrong on our side. Your data is safe. Please try again. |

## Pop-ups (1–7)
All pop-ups behave the same way: they open in 250 ms, Esc or a tap on the backdrop closes them (not while saving), keyboard focus stays inside, and focus returns to the button that opened them.

| # | Pop-up | Opens from | Shows and checks | After "save" |
| --- | --- | --- | --- | --- |
| 1 | Confirm order | "Review order" on screens 5–8 (red version on screen 6) | Service, quantity × price per unit, total, "Cash on delivery", address. Buttons "Confirm order" and "Edit". | Server checks everything again, recalculates the price itself, saves the order, runs smart dispatch → screen 9. A hidden one-time order key stops double orders from a double tap. |
| 2 | Assign or change driver | Screens 14 and 15 | 3 nearest Available drivers with area, distance, ETA, rating; the first marked "Recommended"; "Show all available" opens the rest. If none: "No driver is free right now." | Assignment saved with ETA, tracking row added, new driver Busy, old driver (if changed) Available. |
| 3 | Update status / cancel | Status buttons on screen 14 | "From → To" line. Cancel needs a reason: Customer asked, No driver available, Wrong address, Duplicate order, Other (with text). | Status saved with time, tracking row added, customer sees it within 30 s. |
| 4 | Customer panel | Row on screen 16 (slides in from the right, 420 px) | Details, joined date, orders count, total spent, last 5 orders, Block / Unblock. | Block: confirm → account blocked and logged out everywhere at once; old orders stay. |
| 5 | Add or edit service | Screen 17 | Name (unique), Category (Fuel / Assistance), Unit (litre / service), Price in PKR (above 0), Available. | Saved; customers see the new price on their next page load. |
| 6 | Add or edit driver | Screen 18 | Name, Phone (unique, 03XX format), Vehicle number (unique, like LEA-1234), Area (sets the starting location), Status. | Saved; driver joins dispatch when Available. |
| 7 | Log out | Log out icon or menu | "Log out of AJORA?" with Log out / Stay. | Session ended → Landing page with "You have logged out". |

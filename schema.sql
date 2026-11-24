-- AJORA database schema. Table names are temporary (see CLAUDE.md), to be
-- confirmed against the project ERD. Money is INTEGER paisa; times are UTC
-- ISO-8601 text (see docs/PERFORMANCE.md for the indexes and docs/SECURITY.md
-- for the columns security depends on).

PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id              INTEGER PRIMARY KEY,
  full_name       TEXT NOT NULL,
  email           TEXT NOT NULL UNIQUE,
  phone           TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,
  role            TEXT NOT NULL CHECK (role IN ('customer', 'admin')),
  failed_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until    TEXT,
  session_version INTEGER NOT NULL DEFAULT 0,
  is_active       INTEGER NOT NULL DEFAULT 1,
  created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE services (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  category   TEXT NOT NULL CHECK (category IN ('Fuel', 'Assistance')),
  unit       TEXT NOT NULL CHECK (unit IN ('litre', 'service')),
  price_paisa INTEGER NOT NULL CHECK (price_paisa > 0),
  is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE drivers (
  id             INTEGER PRIMARY KEY,
  name           TEXT NOT NULL,
  phone          TEXT NOT NULL UNIQUE,
  vehicle_number TEXT NOT NULL UNIQUE,
  area           TEXT NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('Available', 'Busy', 'Off duty')) DEFAULT 'Available',
  lat            REAL,
  lng            REAL,
  rating         REAL NOT NULL DEFAULT 5.0,
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE orders (
  id                 INTEGER PRIMARY KEY,
  user_id            INTEGER NOT NULL REFERENCES users (id),
  service_id         INTEGER NOT NULL REFERENCES services (id),
  driver_id          INTEGER REFERENCES drivers (id),
  order_key          TEXT NOT NULL UNIQUE,
  status             TEXT NOT NULL CHECK (status IN ('Pending', 'Assigned', 'On the way', 'Delivered', 'Cancelled')) DEFAULT 'Pending',
  is_emergency       INTEGER NOT NULL DEFAULT 0,
  call_confirmed     INTEGER NOT NULL DEFAULT 1,
  quantity           REAL NOT NULL,
  unit_price_paisa   INTEGER NOT NULL,
  total_paisa        INTEGER NOT NULL,
  address            TEXT,
  landmark           TEXT,
  area               TEXT,
  lat                REAL,
  lng                REAL,
  note               TEXT,
  delivery_time      TEXT NOT NULL CHECK (delivery_time IN ('asap', 'scheduled')) DEFAULT 'asap',
  scheduled_for       TEXT,
  distance_km        REAL,
  predicted_eta_min   INTEGER,
  cancel_reason      TEXT,
  created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  assigned_at        TEXT,
  delivered_at       TEXT
);

CREATE TABLE tracking (
  id         INTEGER PRIMARY KEY,
  order_id   INTEGER NOT NULL REFERENCES orders (id),
  status     TEXT NOT NULL,
  note       TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_orders_user_created ON orders (user_id, created_at);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_emergency_status ON orders (is_emergency, status);
CREATE INDEX idx_drivers_status ON drivers (status);
CREATE INDEX idx_tracking_order ON tracking (order_id);

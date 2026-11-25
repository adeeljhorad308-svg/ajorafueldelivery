-- AJORA database schema, aligned with the FYP document (Chapter 4.2, Tables
-- 35-40). The document is the source of truth for table/column names, types
-- and sizes; see CLAUDE.md's "Database" section for the extra columns it
-- does not list. DECIMAL columns are declared as the document says, but
-- SQLite gives them NUMERIC affinity and stores the value as a float/int
-- regardless (see app/money.py) - every read/write of money goes through
-- that module, never raw SQL arithmetic. Times are UTC, written and read via
-- app/timeutil.py; CURRENT_TIMESTAMP in SQLite is already UTC.

PRAGMA foreign_keys = ON;

CREATE TABLE users (
  user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name            VARCHAR(60) NOT NULL,
  email           VARCHAR(80) NOT NULL UNIQUE,
  phone           VARCHAR(15) NOT NULL UNIQUE,
  password_hash   VARCHAR(255) NOT NULL,
  role            VARCHAR(10) NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
  is_active       BOOLEAN DEFAULT 1,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  -- Extra columns, not in the document (see CLAUDE.md):
  failed_attempts INTEGER DEFAULT 0,
  locked_until    DATETIME,
  session_version INTEGER DEFAULT 0
);

CREATE TABLE services (
  service_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name       VARCHAR(50) NOT NULL UNIQUE,
  category   VARCHAR(30) NOT NULL CHECK (category IN ('Fuel', 'Assistance')),
  unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price > 0),
  unit       VARCHAR(10) NOT NULL CHECK (unit IN ('litre', 'service')),
  available  BOOLEAN DEFAULT 1
);

CREATE TABLE drivers (
  driver_id  INTEGER PRIMARY KEY AUTOINCREMENT,
  name       VARCHAR(60) NOT NULL,
  phone      VARCHAR(15) NOT NULL UNIQUE,
  vehicle_no VARCHAR(15) NOT NULL UNIQUE,
  status     VARCHAR(15) NOT NULL DEFAULT 'Available' CHECK (status IN ('Available', 'Busy', 'Off Duty')),
  latitude   DECIMAL(9, 6),
  longitude  DECIMAL(9, 6),
  rating     DECIMAL(2, 1) CHECK (rating BETWEEN 0 AND 5),
  -- Extra columns, not in the document (see CLAUDE.md):
  area       VARCHAR(50),
  is_active  BOOLEAN DEFAULT 1
);

CREATE TABLE orders (
  order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL REFERENCES users (user_id),
  service_id     INTEGER NOT NULL REFERENCES services (service_id),
  quantity       DECIMAL(8, 2) NOT NULL CHECK (quantity > 0),
  total_amount   DECIMAL(10, 2) NOT NULL,
  address        VARCHAR(200) NOT NULL,
  latitude       DECIMAL(9, 6),
  longitude      DECIMAL(9, 6),
  is_emergency   BOOLEAN DEFAULT 0,
  note           VARCHAR(200),
  scheduled_at   DATETIME,
  status         VARCHAR(20) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Assigned', 'On the Way', 'Delivered', 'Cancelled')),
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  -- Extra columns, not in the document (see CLAUDE.md):
  order_key      TEXT NOT NULL UNIQUE,
  call_confirmed BOOLEAN DEFAULT 1,
  cancel_reason  VARCHAR(200),
  area           VARCHAR(50)
);

-- New table: every driver/ETA/assigned/delivered/distance column that used
-- to live on orders moved here. Changing the driver updates this row;
-- moving an order back to Pending deletes it (tracking keeps the history).
CREATE TABLE assignments (
  assign_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id     INTEGER NOT NULL UNIQUE REFERENCES orders (order_id),
  driver_id    INTEGER NOT NULL REFERENCES drivers (driver_id),
  eta_minutes  INTEGER NOT NULL,
  assigned_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME,
  -- Extra column, not in the document (see CLAUDE.md):
  distance_km  DECIMAL(6, 2)
);

CREATE TABLE tracking (
  track_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id   INTEGER NOT NULL REFERENCES orders (order_id),
  status     VARCHAR(20) NOT NULL CHECK (status IN ('Pending', 'Assigned', 'On the Way', 'Delivered', 'Cancelled')),
  latitude   DECIMAL(9, 6),
  longitude  DECIMAL(9, 6),
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_created ON orders (user_id, created_at);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_emergency_status ON orders (is_emergency, status);
CREATE INDEX idx_assignments_driver ON assignments (driver_id);
CREATE INDEX idx_drivers_status ON drivers (status);
CREATE INDEX idx_tracking_order ON tracking (order_id);
-- Admin dashboard and All orders (C9): date-range filters, newest-first
-- sorting, Due soon and Call needed lists.
CREATE INDEX idx_orders_created_at ON orders (created_at);
CREATE INDEX idx_orders_scheduled_at ON orders (scheduled_at);
CREATE INDEX idx_orders_call_confirmed ON orders (call_confirmed);

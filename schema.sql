CREATE TABLE IF NOT EXISTS tracked_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ebay_item_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    price_ceiling REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ebay_item_id TEXT NOT NULL,
    price REAL NOT NULL,
    shipping REAL,
    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posted_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ebay_item_id TEXT NOT NULL,
    price_at_post REAL NOT NULL,
    fb_post_id TEXT,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ebay_item_id, price_at_post)
);

CREATE INDEX IF NOT EXISTS idx_price_history_item ON price_history (ebay_item_id, seen_at);
CREATE INDEX IF NOT EXISTS idx_posted_deals_item ON posted_deals (ebay_item_id);

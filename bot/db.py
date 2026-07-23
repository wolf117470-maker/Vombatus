import os
import sqlite3
import logging

from bot.config import DB_PATH, SCHEMA_PATH

log = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    log.info("DB initialised at %s", DB_PATH)


def get_active_tracked_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tracked_items WHERE active = 1").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_price(ebay_item_id, price, shipping):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO price_history (ebay_item_id, price, shipping) VALUES (?, ?, ?)",
        (ebay_item_id, price, shipping),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_baseline(ebay_item_id, exclude_id):
    """Average price of prior readings for this item, excluding the reading
    just inserted (exclude_id). Returns (baseline, prior_count); baseline is
    None if prior_count < 3 — not enough history to trust yet."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT AVG(price) as avg_price, COUNT(*) as cnt
        FROM price_history
        WHERE ebay_item_id = ? AND id != ?
        """,
        (ebay_item_id, exclude_id),
    ).fetchone()
    conn.close()
    cnt = row["cnt"] if row else 0
    if cnt < 3:
        return None, cnt
    return row["avg_price"], cnt


def get_min_posted_price(ebay_item_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT MIN(price_at_post) as min_price FROM posted_deals WHERE ebay_item_id = ?",
        (ebay_item_id,),
    ).fetchone()
    conn.close()
    return row["min_price"] if row and row["min_price"] is not None else None


def log_posted_deal(ebay_item_id, price_at_post, fb_post_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO posted_deals (ebay_item_id, price_at_post, fb_post_id) VALUES (?, ?, ?)",
        (ebay_item_id, price_at_post, fb_post_id),
    )
    conn.commit()
    conn.close()


def get_recent_posted_deals(limit=20):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT pd.*, ti.title, ti.brand, ti.category
        FROM posted_deals pd
        JOIN tracked_items ti ON ti.ebay_item_id = pd.ebay_item_id
        ORDER BY pd.posted_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tracked_items_summary():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT ti.id, ti.ebay_item_id, ti.title, ti.brand, ti.category,
               ti.price_ceiling, ti.active,
               COUNT(ph.id) as readings,
               MIN(ph.price) as min_price, AVG(ph.price) as avg_price, MAX(ph.price) as max_price,
               MAX(ph.seen_at) as last_seen
        FROM tracked_items ti
        LEFT JOIN price_history ph ON ph.ebay_item_id = ti.ebay_item_id
        GROUP BY ti.id
        ORDER BY ti.title
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

import os
import logging
import tempfile
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bot.config import DEAL_THRESHOLD_PCT, POLL_INTERVAL_HOURS
from bot.db import (
    get_active_tracked_items, insert_price, get_baseline,
    get_min_posted_price, log_posted_deal,
)
from bot.ebay_client import get_item
from bot.image_gen import generate_deal_card
from bot.facebook import post_photo, build_caption

log = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Australia/Brisbane")

_scan_lock = threading.Lock()


def scan_and_post():
    """Guards against overlapping runs (e.g. startup scan + manual /scan
    trigger landing at the same time) — same lock pattern BFD added after a
    real duplicate-post incident."""
    if not _scan_lock.acquire(blocking=False):
        log.info("Scan already in progress — skipping this trigger")
        return
    try:
        _scan_and_post()
    finally:
        _scan_lock.release()


def _scan_and_post():
    items = get_active_tracked_items()
    log.info("=== Scan started — %d active tracked items ===", len(items))
    for item in items:
        _check_item(item)
    log.info("=== Scan complete ===")


def _check_item(item):
    ebay_item_id = item["ebay_item_id"]
    live = get_item(ebay_item_id)
    if not live:
        log.warning("No eBay data for %s (%s) — skipping", ebay_item_id, item["title"])
        return

    reading_id = insert_price(ebay_item_id, live["price"], live["shipping"])
    baseline, prior_count = get_baseline(ebay_item_id, reading_id)

    if baseline is None:
        log.debug("%s: warming up (%d/3 prior readings)", ebay_item_id, prior_count)
        return

    price = live["price"]

    if price > item["price_ceiling"]:
        log.debug("%s: A$%.2f above ceiling A$%.2f — skip", ebay_item_id, price, item["price_ceiling"])
        return

    if price > baseline * (1 - DEAL_THRESHOLD_PCT):
        log.debug("%s: A$%.2f not %.0f%% below baseline A$%.2f", ebay_item_id, price, DEAL_THRESHOLD_PCT * 100, baseline)
        return

    floor = get_min_posted_price(ebay_item_id)
    if floor is not None and price >= floor:
        log.info("%s: A$%.2f not lower than prior posted floor A$%.2f — skip repost", ebay_item_id, price, floor)
        return

    pct_below = (baseline - price) / baseline * 100
    _post_deal(item, live, price, pct_below)


def _post_deal(item, live, price, pct_below):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img_path = tmp.name

    try:
        generate_deal_card(item, live, pct_below, img_path)
        caption = build_caption(item, live, pct_below)
        post_id = post_photo(img_path, caption)

        if post_id:
            log_posted_deal(item["ebay_item_id"], price, post_id)
            log.info("Posted deal: %s A$%.2f (%.1f%% off) — FB post %s",
                      item["title"], price, pct_below, post_id)
        else:
            log.error("FB post failed for %s", item["title"])
    finally:
        if os.path.exists(img_path):
            os.unlink(img_path)


def start_scheduler():
    scheduler.add_job(
        scan_and_post,
        trigger=IntervalTrigger(hours=POLL_INTERVAL_HOURS),
        id="scan_and_post",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler started — polling every %dh", POLL_INTERVAL_HOURS)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()

import logging
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string

from bot.db import init_db, get_recent_posted_deals, get_tracked_items_summary
from bot.deal_engine import start_scheduler, scan_and_post
from bot.facebook import verify_token
from bot.config import POLL_INTERVAL_HOURS, DEAL_THRESHOLD_PCT, DASHBOARD_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)

STATUS_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Sparky Trade Deals Bot</title>
<style>
  body { font-family: monospace; background: #0f172a; color: #e2e8f0; padding: 2rem; }
  h1 { color: #fbbf24; } h2 { color: #94a3b8; border-bottom: 1px solid #334155; padding-bottom: 4px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; }
  th { background: #1e293b; color: #fbbf24; padding: 8px 12px; text-align: left; }
  td { padding: 6px 12px; border-bottom: 1px solid #1e293b; }
  tr:hover td { background: #1e293b; }
  .pill { display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 0.85em; }
  .green { background: #14532d; color: #22c55e; }
  .amber { background: #451a03; color: #fbbf24; }
  .red { background: #450a0a; color: #f87171; }
  .config { background: #1e293b; padding: 1rem; border-radius: 8px; margin-bottom: 2rem; }
  .config span { color: #fbbf24; }
</style>
</head>
<body>
<h1>⚡ Sparky Trade Deals Bot</h1>
<div class="config">
  Threshold: <span>{{ threshold }}% below baseline</span> &nbsp;|&nbsp;
  Poll: <span>every {{ poll_hours }}h</span> &nbsp;|&nbsp;
  FB Token: <span class="pill {{ 'green' if fb_ok else 'amber' }}">{{ 'OK' if fb_ok else 'FAIL' }}</span>
</div>

<h2>Recent Posts ({{ posts|length }})</h2>
<table>
  <tr><th>Item</th><th>Brand</th><th>Price</th><th>Posted</th><th>FB Post ID</th></tr>
  {% for p in posts %}
  <tr>
    <td>{{ p.title }}</td>
    <td>{{ p.brand or '—' }}</td>
    <td>A${{ '%.2f'|format(p.price_at_post) }}</td>
    <td>{{ p.posted_at[:16] }}</td>
    <td><small>{{ p.fb_post_id }}</small></td>
  </tr>
  {% endfor %}
</table>

<h2>Tracked Items ({{ items|length }})</h2>
<table>
  <tr><th>Item</th><th>Brand</th><th>Ceiling</th><th>Active</th><th>Readings</th><th>Min</th><th>Avg</th><th>Max</th><th>Last Seen</th></tr>
  {% for i in items %}
  <tr>
    <td>{{ i.title }}</td>
    <td>{{ i.brand or '—' }}</td>
    <td>A${{ '%.2f'|format(i.price_ceiling) }}</td>
    <td><span class="pill {{ 'green' if i.active else 'red' }}">{{ 'yes' if i.active else 'no' }}</span></td>
    <td>{{ i.readings }}</td>
    <td>{{ 'A$%.2f'|format(i.min_price) if i.min_price is not none else '—' }}</td>
    <td>{{ 'A$%.2f'|format(i.avg_price) if i.avg_price is not none else '—' }}</td>
    <td>{{ 'A$%.2f'|format(i.max_price) if i.max_price is not none else '—' }}</td>
    <td>{{ i.last_seen[:16] if i.last_seen else '—' }}</td>
  </tr>
  {% endfor %}
</table>
</body>
</html>
"""


@app.route("/")
def status():
    fb_ok = verify_token()
    return render_template_string(
        STATUS_PAGE,
        threshold=DEAL_THRESHOLD_PCT * 100,
        poll_hours=POLL_INTERVAL_HOURS,
        fb_ok=fb_ok,
        posts=get_recent_posted_deals(20),
        items=get_tracked_items_summary(),
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/scan", methods=["POST"])
def trigger_scan():
    """Manually trigger a scan via POST /scan"""
    t = threading.Thread(target=scan_and_post, daemon=True)
    t.start()
    return jsonify({"status": "scan triggered"})


if __name__ == "__main__":
    log.info("Initialising DB...")
    init_db()

    log.info("Starting scheduler...")
    start_scheduler()

    # Run one scan immediately on startup
    log.info("Running initial scan...")
    t = threading.Thread(target=scan_and_post, daemon=True)
    t.start()

    log.info("Starting Flask on :%d", DASHBOARD_PORT)
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=False, use_reloader=False)

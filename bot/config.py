import os

EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID", "")
EBAY_EPN_CAMPAIGN_ID = os.getenv("EBAY_EPN_CAMPAIGN_ID", "")
EBAY_MARKETPLACE = os.getenv("EBAY_MARKETPLACE", "EBAY-AU")
# "sandbox" or "production" — sandbox keys (App ID containing "-SBX-") only
# work against api.sandbox.ebay.com, not api.ebay.com.
EBAY_ENV = os.getenv("EBAY_ENV", "production")

FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
FB_GRAPH_VERSION = "v25.0"

POLL_INTERVAL_HOURS = int(os.getenv("POLL_INTERVAL_HOURS", "4"))
# Fraction (0-1), not a percentage — 0.20 means "20% below baseline".
DEAL_THRESHOLD_PCT = float(os.getenv("DEAL_THRESHOLD_PCT", "0.20"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8084"))

DB_PATH = os.getenv("DB_PATH", "/data/sparky.db")
SCHEMA_PATH = os.getenv(
    "SCHEMA_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql"),
)

import time
import base64
import logging
import requests

from bot.config import EBAY_APP_ID, EBAY_CERT_ID, EBAY_MARKETPLACE, EBAY_EPN_CAMPAIGN_ID, EBAY_ENV

log = logging.getLogger(__name__)

_API_HOST = "api.sandbox.ebay.com" if EBAY_ENV == "sandbox" else "api.ebay.com"
OAUTH_URL = f"https://{_API_HOST}/identity/v1/oauth2/token"
BROWSE_BASE = f"https://{_API_HOST}/buy/browse/v1"

_token_cache = {"token": None, "expires_at": 0}


def _get_access_token():
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    if not EBAY_APP_ID or not EBAY_CERT_ID:
        log.error("eBay App ID/Cert ID not configured")
        return None

    creds = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
    try:
        resp = requests.post(
            OAUTH_URL,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 7200)
        return _token_cache["token"]
    except Exception as e:
        log.error("eBay OAuth token request failed: %s", e)
        return None


def get_item(ebay_item_id):
    """Fetch live price/shipping/affiliate link for one eBay item via the
    Browse API. Returns None on any failure (missing listing, ended listing,
    API/auth error) — never fabricate a price, mirrors BFD's degrade-safe
    client pattern."""
    token = _get_access_token()
    if not token:
        return None

    url = f"{BROWSE_BASE}/item/{ebay_item_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": EBAY_MARKETPLACE,
        # Populates itemAffiliateWebUrl in the response with a ready-to-use
        # EPN affiliate link — no manual URL construction needed.
        "X-EBAY-C-ENDUSERCTX": f"affiliateCampaignId={EBAY_EPN_CAMPAIGN_ID}",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            log.warning("eBay item %s not found (404) — listing may have ended", ebay_item_id)
            return None
        resp.raise_for_status()
        data = resp.json()

        price = float(data["price"]["value"])

        shipping = None
        shipping_options = data.get("shippingOptions") or []
        if shipping_options:
            cost = shipping_options[0].get("shippingCost", {}).get("value")
            shipping = float(cost) if cost is not None else 0.0

        return {
            "title": data.get("title"),
            "price": price,
            "shipping": shipping,
            "currency": data["price"].get("currency", "AUD"),
            "affiliate_link": data.get("itemAffiliateWebUrl") or data.get("itemWebUrl"),
            "condition": data.get("condition"),
            "image_url": (data.get("image") or {}).get("imageUrl"),
        }
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        log.error("eBay getItem failed for %s: %s", ebay_item_id, detail)
        return None
    except Exception as e:
        log.error("eBay getItem error for %s: %s", ebay_item_id, e)
        return None

import requests
import logging
from bot.config import FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, FB_GRAPH_VERSION

log = logging.getLogger(__name__)

GRAPH_BASE = f"https://graph.facebook.com/{FB_GRAPH_VERSION}"


def build_caption(item, live, pct_below):
    price = live["price"]
    shipping = live.get("shipping")
    if shipping == 0:
        ship_txt = "Free shipping"
    elif shipping is not None:
        ship_txt = f"+A${shipping:.2f} shipping"
    else:
        ship_txt = ""

    brand = item.get("brand") or ""
    title = item.get("title") or live.get("title") or "Deal"
    link = live.get("affiliate_link") or ""

    lines = [
        f"⚡ ELECTRICAL DEAL: {title}",
        "",
        f"💰 A${price:.2f}" + (f"  ·  {ship_txt}" if ship_txt else ""),
    ]
    if pct_below and pct_below > 0:
        lines.append(f"🔥 {pct_below:.0f}% below the recent average price!")
    lines += [
        "",
        f"👉 Grab it here (prices change fast!): {link}",
        "",
        "💡 Tip: Confirm the exact model/variant and check seller feedback before buying.",
        "",
        "Follow Sparky Trade Deals for more electrical test tool deals! 🔌",
        "",
    ]
    tags = ["#ElectricalDeals", "#TestTools", "#TradieTools", "#eBayDeals", "#Australia"]
    if brand:
        tags.insert(1, f"#{brand.replace(' ', '')}")
    lines.append(" ".join(tags))
    return "\n".join(lines)


def post_photo(image_path, caption):
    """Post image + caption to Facebook page. Returns post ID or None."""
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        log.error("Facebook credentials not configured")
        return None

    url = f"{GRAPH_BASE}/{FB_PAGE_ID}/photos"
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(url, data={
                "message": caption,
                "access_token": FB_PAGE_ACCESS_TOKEN,
            }, files={"source": ("deal.png", f, "image/png")}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        post_id = data.get("post_id") or data.get("id")
        log.info("Posted to Facebook: %s", post_id)
        return post_id
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else ""
        if e.response is not None:
            try:
                err = e.response.json().get("error", {})
                detail = "{} (code={}, subcode={})".format(
                    err.get("message", detail), err.get("code"), err.get("error_subcode")
                )
            except ValueError:
                pass
        log.error("Facebook post failed: %s", detail or e)
        return None
    except Exception as e:
        log.error("Facebook post error: %s", e)
        return None


def verify_token():
    """Check FB token is valid. Returns True/False."""
    url = f"{GRAPH_BASE}/me"
    try:
        resp = requests.get(url, params={"access_token": FB_PAGE_ACCESS_TOKEN}, timeout=10)
        data = resp.json()
        if "error" in data:
            log.error("FB token invalid: %s", data["error"].get("message"))
            return False
        log.info("FB token OK — page: %s", data.get("name", "unknown"))
        return True
    except Exception as e:
        log.error("FB token check failed: %s", e)
        return False

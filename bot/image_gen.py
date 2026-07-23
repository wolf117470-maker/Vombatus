import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

# Card dimensions (same as BFD)
W, H = 1200, 630

# Colours — reused exactly from BFD's navy/gold theme
BG_TOP    = (15, 23, 42)      # dark navy
BG_BOT    = (30, 41, 59)      # slightly lighter navy
ACCENT    = (251, 191, 36)    # amber/gold
WHITE     = (255, 255, 255)
GREY      = (148, 163, 184)
GREEN     = (34, 197, 94)
PILL_BG   = (251, 191, 36)
PILL_TEXT = (15, 23, 42)


def _font(size, bold=False):
    candidates = [
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _gradient_bg(draw, w, h):
    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _pill(draw, x, y, text, bg=PILL_BG, fg=PILL_TEXT, font=None):
    if font is None:
        font = _font(22, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 18, 8
    draw.rounded_rectangle([x, y, x + tw + pad_x * 2, y + th + pad_y * 2], radius=20, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return x + tw + pad_x * 2


def generate_deal_card(item, live, pct_below, output_path):
    """
    Generate a deal card image and save to output_path.
    item: dict row from tracked_items
    live: dict from ebay_client.get_item()
    pct_below: float percentage below baseline
    """
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw, W, H)

    # Decorative side bar
    draw.rectangle([0, 0, 8, H], fill=ACCENT)

    draw.text((40, 35), "⚡ ELECTRICAL DEAL ALERT", font=_font(24, bold=True), fill=ACCENT)

    # Title (wrapped, max 2 lines)
    title = item.get("title") or live.get("title") or "Deal"
    wrapped = textwrap.wrap(title, width=28)[:2]
    y = 90
    for line in wrapped:
        draw.text((40, y), line, font=_font(44, bold=True), fill=WHITE)
        y += 54

    brand_cat = "  ·  ".join(x for x in [item.get("brand"), item.get("category")] if x)
    if brand_cat:
        draw.text((40, y + 10), brand_cat, font=_font(26), fill=GREY)

    # Divider
    draw.line([(40, 230), (W - 40, 230)], fill=(51, 65, 85), width=2)

    # Price (big)
    price_txt = f"A${live['price']:.2f}"
    draw.text((40, 255), price_txt, font=_font(110, bold=True), fill=ACCENT)

    shipping = live.get("shipping")
    if shipping == 0:
        ship_txt = "Free shipping"
    elif shipping is not None:
        ship_txt = f"+A${shipping:.2f} shipping"
    else:
        ship_txt = "shipping varies"
    draw.text((40, 400), ship_txt, font=_font(20), fill=GREY)

    # Saving pill
    if pct_below and pct_below > 0:
        _pill(draw, 40, 450,
              f"🔥 {pct_below:.0f}% BELOW AVERAGE",
              bg=GREEN, fg=(255, 255, 255),
              font=_font(22, bold=True))

    condition = live.get("condition") or ""
    if condition:
        draw.text((40, 510), condition, font=_font(28), fill=WHITE)

    # Right side — CTA box
    box_x = 800
    draw.rounded_rectangle([box_x, 60, W - 40, 590], radius=16,
                            fill=(30, 41, 59), outline=ACCENT, width=2)
    draw.text((box_x + 30, 85), "GRAB THIS DEAL", font=_font(26, bold=True), fill=ACCENT)
    draw.text((box_x + 30, 130), "Prices change fast —", font=_font(20), fill=GREY)
    draw.text((box_x + 30, 158), "tap the link to lock it in.", font=_font(20), fill=GREY)
    draw.text((box_x + 30, 210), "🔗 Link in post caption", font=_font(22, bold=True), fill=WHITE)

    draw.line([(box_x + 30, 265), (W - 70, 265)], fill=(51, 65, 85), width=1)

    tips = [
        "✓ Sold via eBay Australia",
        "✓ Check seller feedback",
        "✓ Prices in AUD",
        "✓ Confirm model/variant before buying",
    ]
    for i, tip in enumerate(tips):
        draw.text((box_x + 30, 285 + i * 42), tip, font=_font(20), fill=GREY)

    # Footer
    draw.rectangle([0, H - 50, W, H], fill=(15, 23, 42))
    draw.text((40, H - 35), "Prices sourced via eBay Partner Network · Always verify before buying · Availability subject to change",
              font=_font(16), fill=(71, 85, 105))

    img.save(output_path, "PNG", quality=95)
    return output_path

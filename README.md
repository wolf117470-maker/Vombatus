# Sparky Trade Deals Bot

Sister bot to [BFD](https://github.com/wolf117470-maker/BFD) (flight-deals-bot),
same owner (Vombatus Solutions). Polls eBay listings for electrical test tools
(multimeters, clamp meters, insulation testers, basic hand tools), detects
price drops against a rolling baseline, and posts deal cards to the
**Sparky Trade Deals** Facebook page.

Architecture mirrors BFD exactly: Python + Docker Compose + SQLite +
APScheduler + Pillow + Facebook Graph API. Data source is the **eBay Partner
Network Browse API** (AU marketplace) — not scraping, not Amazon PA-API (that
may come later for the sister project, see the electrical-meters deals site).

## Schema

- `tracked_items` — the curated list of eBay listings to watch. `active=0` is
  a manual veto (hard skip, no other condition overrides it).
- `price_history` — every price reading, kept indefinitely.
- `posted_deals` — what's actually been posted to Facebook, with
  `UNIQUE(ebay_item_id, price_at_post)`.

## Deal logic (`bot/deal_engine.py`)

1. Poll every `POLL_INTERVAL_HOURS` (default 4).
2. Insert the new reading, then compute baseline = average of all **prior**
   `price_history` rows for that item (current reading excluded by row id).
   Needs 3+ prior readings to trust the baseline — at the default 4h poll
   interval that's a **~12h warm-up**, not 48-72h. If you actually want a
   longer warm-up, that needs an explicit time-based check (e.g. "3+ readings
   spanning at least 48h"), not just a row count — flag if you want that
   added.
3. Deal fires if `current_price <= baseline * (1 - DEAL_THRESHOLD_PCT)` AND
   `current_price <= tracked_items.price_ceiling`.
4. Dedupe: re-post only allowed if price is lower than the minimum price this
   item has ever been posted at (`MIN(price_at_post)` in `posted_deals`).
5. `active=0` skips the item entirely before any of the above runs.

Same overlapping-scan guard as BFD (`threading.Lock` around `scan_and_post`)
— BFD double-posted to its live Facebook page once from a race between a
startup scan and a manual `/scan` trigger; this repo starts with the fix
already in place rather than rediscovering it.

## Deploy (later — not done yet)

Target: `/opt/sparky-deals-bot` on CT101 (192.168.50.104), dashboard port
8084 (8082 = crypto-agent, 8083 = BFD, both already taken). Not attempted in
this pass — repo only, per instruction to stop after commit/push and review
first.

## Two blocking prerequisites

### 1. eBay Developer App — sandbox keys obtained, production still outstanding

Sandbox App ID/Cert ID were issued and verified working 2026-07-24 (OAuth
client-credentials token request returns 200). `bot/ebay_client.py` now reads
`EBAY_ENV` (`sandbox` or `production`) to pick the right API host
(`api.sandbox.ebay.com` vs `api.ebay.com`) — sandbox and production keysets
are not interchangeable, using a sandbox App ID against the production host
(or vice versa) fails auth. Sandbox is only useful for exercising the
OAuth/API code path — it has no real AU marketplace listings, so the bot
can't actually post real deals until production keys are in.

1. Go to https://developer.ebay.com and sign in with the account that has the
   EPN campaign (`vombatussolutions`).
2. Apply for a **Production** keyset under "My Account → Application Keys".
   This is a manual application — eBay reviews it before issuing production
   keys, unlike the sandbox keys (instant) or the EPN signup (also instant).
3. Once approved, create a keyset for the AU marketplace. You'll get three
   values: **App ID (Client ID)**, **Cert ID (Client Secret)**, **Dev ID**.
   Only App ID + Cert ID are actually used by the Browse API OAuth flow this
   bot uses; Dev ID is issued alongside them as part of eBay's standard
   three-key set and is kept in `.env` for completeness / possible future
   Trading API use, but isn't called anywhere yet.
4. Put them in `.env` as `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID`, and set
   `EBAY_ENV=production`.
5. `EBAY_EPN_CAMPAIGN_ID=5339166286` is already confirmed active — no action
   needed there.

### 2. Facebook Page Access Token for "Sparky Trade Deals" — not generated yet

Reuses the **existing** Meta app (ID `1732187907801249`, Vombatus Solutions
business portfolio, already verified from BFD) — do not create a new app.

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/),
   select app `1732187907801249`.
2. Under permissions, request `pages_show_list`, `pages_manage_posts`,
   `pages_read_engagement` (same set BFD uses).
3. Call `GET /me/accounts` — this returns every Page the authenticated user
   manages, each with its own short-lived Page Access Token. Find the entry
   for "Sparky Trade Deals" and copy its `access_token`.
4. Exchange it for a **long-lived** token: `GET /oauth/access_token?
   grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}
   &fb_exchange_token={short-lived-page-token}`. Page tokens derived from a
   long-lived user token don't expire, same as BFD's setup.
5. Put the Page ID and long-lived token in `.env` as `FB_PAGE_ID` and
   `FB_PAGE_ACCESS_TOKEN`.

Until both of these are done, `bot/ebay_client.py` and `bot/facebook.py` will
log errors and return `None`/skip — no fake data, no crash, same degrade-safe
pattern as BFD and the electrical-meters deals site.

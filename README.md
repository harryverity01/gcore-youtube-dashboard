# Gcore · YouTube Performance Dashboard

A self-updating, static dashboard for the **@gcoreofficial** YouTube channel —
live channel stats, 28-day analytics, a thumbnail wall of top videos, and the
Phase-2 growth strategy in one shareable page. Rebuilt and redeployed every
morning by GitHub Actions.

**Live URL:** _(set after first deploy — Settings → Pages)_

## How it works

```
fetch_gcore_stats.py   →  docs/data.json   (YouTube Data + Analytics API)
strategy.json          ─┐
build.py               ─┴→ docs/index.html (static, self-contained)
.github/workflows/daily.yml → fetch → build → deploy to GitHub Pages (daily 06:20 UTC)
```

- **`fetch_gcore_stats.py`** — refreshes an OAuth token and pulls channel
  snapshot, 28-day overview (vs prior 28d), daily trend, traffic sources,
  geography, demographics, content-type split, and the top 25 videos with
  durations. Writes `docs/data.json`.
- **`strategy.json`** — the editorial strategy shown on the page (mission,
  Phase-2 targets, "what's working", "next up"). **Edit this by hand** when the
  Growth Plan changes; the numbers come from the API automatically.
- **`build.py`** — injects both JSON blobs into a single static `index.html`
  (Chart.js from CDN, thumbnails from `i.ytimg.com`). No server, no database.

## Run locally

```bash
python3 fetch_gcore_stats.py docs/data.json   # needs ~/.youtube-mcp-gcore/token.json
python3 build.py
python3 -m http.server 8753 --directory docs   # open http://localhost:8753
```

## Daily auto-update (already configured)

The workflow runs on a daily cron, on every push to `main`, and on manual
dispatch. It needs one repo secret:

- **`GCORE_TOKEN_JSON`** — the full contents of `~/.youtube-mcp-gcore/token.json`
  (client_id, client_secret, refresh_token, token_uri). Set via
  `Settings → Secrets and variables → Actions → New repository secret`.

GitHub Pages must be set to **Source: GitHub Actions** (Settings → Pages).

## Notes

- The page carries `noindex, nofollow` so it won't show up in search. The data
  is still served at a public URL — share it deliberately. For true privacy use
  a private repo (needs a paid GitHub plan for Pages).
- Thumbnail CTR / impressions are **Studio-only** (no API) and are not shown.
- The channel is not monetised, so no revenue metrics appear.

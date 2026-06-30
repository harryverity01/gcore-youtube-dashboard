# Gcore · YouTube Performance Dashboard

A self-updating, static dashboard for the **@gcoreofficial** YouTube channel.
Every panel responds to a **date range you choose in the browser** — presets
(7 / 28 / 90 days, this month, last month, all-time) or any custom start/end.
Rebuilt and redeployed every morning by GitHub Actions.

**Live URL:** _(set after first deploy — Settings → Pages)_

## How it works

```
fetch_gcore_stats.py   →  docs/data.json   (Data API + Analytics API + Reporting API)
strategy.json          ─┐
build.py               ─┴→ docs/index.html (static, self-contained, range-driven)
.github/workflows/daily.yml → fetch → build → deploy to GitHub Pages (daily 06:20 UTC)
```

Because the page is static GitHub Pages, the browser **can't call the API live**
(the OAuth refresh token stays server-side — auth is untouched). Instead the
fetch script bakes **day-level rows once per day** and the page aggregates
whatever range you pick **entirely client-side**.

- **`fetch_gcore_stats.py`** — refreshes the OAuth token and pulls:
  - channel snapshot + per-video metadata (**Data API v3**),
  - a full-history per-day channel series and a per-video per-day series for the
    last 365 days, plus an all-time per-video table, traffic/content per-day, and
    geography/demographics per preset window (**Analytics API v2**),
  - thumbnail **impressions + CTR** via the **Reporting API v1** reach reports
    (`channel_reach_basic_a1`) — it checks for an existing reporting job and
    **creates one if missing**, then downloads & parses the daily CSVs.
  - Writes `docs/data.json`. Degrades gracefully — a failing call never breaks the build.
- **`strategy.json`** — the editorial strategy shown on the page (mission,
  targets, "what's working", "next up"). **Edit by hand**; the numbers come from
  the API automatically. `editorial_since` sets the "Editorial only" cutoff.
- **`build.py`** — renders a single static `index.html`: a reactive client app
  (date-range state + aggregation + charts/tables), Chart.js from CDN, thumbnails
  from `i.ytimg.com`. No server, no database.

### Panels (all respect the active range unless noted)

| Panel | Source |
|---|---|
| Channel snapshot (subs, total views, videos, age) | Data API — **lifetime**, not range-dependent |
| Performance cards (views, watch time, avg view duration, net subs, likes, comments, shares) + deltas | Analytics per-day series, aggregated for the range vs the previous equal-length period |
| Daily breakdown (line chart + table) | Analytics `day` dimension |
| Top videos (sortable: total views, watch time, avg duration, avg % viewed, impressions, CTR) | **Lifetime totals per video** (not range-dependent): total views from the Data API, watch time/avg duration/avg % viewed from all-time Analytics, impressions/CTR live from the Reporting API |
| Traffic sources / Content type | Analytics `day,insightTrafficSourceType` / `day,creatorContentType` |
| Geography / Audience age | Analytics per **preset window** (geo has too many keys; `viewerPercentage` can't be sliced by day) |

See **[METRICS.md](METRICS.md)** for the exact API metric behind every number.

## Impressions & CTR (fully automated)

Impressions/CTR are **not** in the Analytics API — they come from the
**Reporting API** reach report `channel_reach_basic_a1` and update on the same
daily schedule as everything else, with **no manual step**. The fetch script
check-or-creates the reporting job each run, downloads the daily CSVs, and bakes
per-video impressions + clicks; the Top Videos table shows each video's
cumulative impressions and CTR (live), growing daily.

Job-based limitation (YouTube's): data starts ~24–48h after the job is first
created and the API only provides ~30 days of history to begin with, so older
dates show **n/a** until they fill in going forward.

## Run locally

```bash
python3 fetch_gcore_stats.py docs/data.json   # needs ~/.youtube-mcp-gcore/token.json
python3 build.py
python3 -m http.server 8753 --directory docs   # open http://localhost:8753
```

## Daily auto-update (already configured)

Daily cron + push-to-`main` + manual dispatch. One repo secret:

- **`GCORE_TOKEN_JSON`** — full contents of `~/.youtube-mcp-gcore/token.json`
  (client_id, client_secret, refresh_token, token_uri). Set via
  `Settings → Secrets and variables → Actions → New repository secret`.

GitHub Pages must be **Source: GitHub Actions** (Settings → Pages).

**Reporting API note:** the reach job needs the *YouTube Reporting API* enabled
on the OAuth app's Google Cloud project (one-time). The same
`yt-analytics.readonly` scope already used by the Analytics API covers it, so the
token is unchanged. If the API isn't enabled, the dashboard still builds and the
reach job card says so.

## Notes

- The page carries `noindex, nofollow`. The data is still served at a public URL —
  share deliberately. For true privacy use a private repo (paid plan for Pages).
- The channel is not monetised, so no revenue metrics appear.

# Metrics reference — what API field backs each number

Every panel is computed **in the browser** for the active date range from
day-level rows baked into `docs/data.json` by `fetch_gcore_stats.py`. Ranges are
inclusive `[start, end]` in UTC dates (matching the API `day` dimension).

## Channel Snapshot (lifetime — not range-dependent)

| Number | Source |
|---|---|
| Subscribers | Data API `channels.statistics.subscriberCount` |
| Total Views | Data API `channels.statistics.viewCount` |
| Videos | Data API `channels.statistics.videoCount` |
| Channel age | derived from `channels.snippet.publishedAt` |

## Performance cards (active range, vs previous equal-length period)

All from the Analytics API v2, `dimensions=day` over the full channel history,
summed for the range. Deltas compare to the immediately preceding period of the
same length.

| Card | Analytics metric |
|---|---|
| Views | `views` |
| Watch time | `estimatedMinutesWatched` (shown in hours) |
| Avg view duration | computed exactly = Σ(`estimatedMinutesWatched`×60) ÷ Σ`views` (seconds) |
| Net subs | `subscribersGained` − `subscribersLost` |
| Likes / Comments / Shares | `likes` / `comments` / `shares` |
| Subs gained / lost | `subscribersGained` / `subscribersLost` |

## Daily Breakdown (line chart + table)

Analytics `dimensions=day`, one row per day in range:

| Column | Analytics metric |
|---|---|
| Views | `views` |
| Watch time | `estimatedMinutesWatched` |
| Avg view duration | `averageViewDuration` (per-day, seconds); the table total recomputes it as Σwatch-seconds ÷ Σviews |

*The chart buckets to weekly when a range exceeds ~140 days, for readability; the
table stays daily (latest 800 rows shown for very long ranges).*

## Top Videos (sortable, active range)

Two modes, shown in the caption under the table:

- **Range mode** (range within the last 365 days): per-video `dimensions=day,
  filters=video==<id>` summed for the range, re-ranked live.
- **All-time mode** (range = all-time, or it extends before the 365-day per-video
  window): the all-time per-video table (`dimensions=video` over channel history).

| Column | Source |
|---|---|
| Views | Analytics `views` |
| Watch time | Analytics `estimatedMinutesWatched` (hours) |
| Avg duration | Analytics `averageViewDuration` (range = Σwatch-seconds ÷ Σviews) |
| Avg % viewed | Analytics `averageViewPercentage` (views-weighted across the range) |
| Impressions | Reporting API `video_thumbnail_impressions` (live) or Studio import |
| CTR | Reporting API `video_thumbnail_impressions_ctr` (live) or Studio import |

CTR/impressions precedence per video+range: **live** reach data → **imported**
Studio value → **n/a**.

## Traffic sources / Content type (active range)

Analytics `dimensions=day,insightTrafficSourceType` and `day,creatorContentType`
(metrics `views`, `estimatedMinutesWatched`), summed for the range. Per-day data
covers the last 365 days; for ranges that extend earlier the panel caption notes
the coverage.

## Geography / Audience age (nearest preset window)

These can't be sliced by an arbitrary range:
- Geography has ~200 country keys — per-day rows would blow the API row caps.
- `viewerPercentage` (demographics) **cannot** be combined with the `day`
  dimension at all.

So both are baked per **preset window** (7 / 28 / 90 / 365 days, all-time). The
page picks the nearest window for the active range and labels it in the caption.

| Panel | Analytics |
|---|---|
| Top geographies | `dimensions=country`, metric `views` |
| Audience by age | `dimensions=ageGroup,gender`, metric `viewerPercentage` (summed across gender) |

---

# Impressions & CTR

## A. Reporting API reach reports (automated)

- Report type: **`channel_reach_basic_a1`**
  - Dimensions: `date`, `channel_id`, `video_id`
  - Metrics: `video_thumbnail_impressions`, `video_thumbnail_impressions_ctr`
- The fetch script lists reporting jobs, finds the one for this report type, and
  **creates it if missing** (`name: gcore-dashboard-reach`). It then downloads the
  daily report CSVs, parses the header to locate the columns (no hard-coded
  positions), and bakes per (video, day): **impressions** and **clicks**
  (clicks = impressions × CTR, with the CTR fraction/percent unit auto-detected).
  The page recomputes range CTR = Σclicks ÷ Σimpressions, so any sub-range
  aggregates correctly.
- **Timing:** the Reporting API is job-based — data only starts **~24–48h after
  the job is created** and backfills **~30 days max**.

## B. Manual Studio import (for older history)

On the page: **Impressions & CTR → Import Studio CSV**. Parsed in-browser,
persisted in `localStorage`, joined onto videos by **video ID**. Use it to load
history the reporting job can't backfill.

### Exact export to use

YouTube Studio → **Analytics** → **Advanced mode** → **Content** tab →
**Export current view → Comma-separated values (.csv)** → open the
**`Table data.csv`** from the downloaded zip.

The importer matches columns **by header name** (any order, extra columns
ignored). It needs:

| Column header (as Studio exports it) | Used for |
|---|---|
| `Video` | the 11-char video ID (the join key; the `Total` row is skipped) |
| `Impressions` | impressions |
| `Impressions click-through rate (%)` | CTR (percent) |

`Content` is accepted as an alias for `Video`; any header containing
`click-through`/`ctr` is accepted for CTR. Commas, spaces and a trailing `%` are
stripped from numbers. See **`studio_import_example.csv`** for the exact shape.

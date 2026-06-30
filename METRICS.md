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

## Top Videos (sortable)

**Lifetime totals per video — not affected by the date range above.** Sortable by
any column.

| Column | Source |
|---|---|
| Total views | **Data API** `videos.statistics.viewCount` — the lifetime count YouTube shows on the video |
| Watch time | Analytics `estimatedMinutesWatched`, all-time (`dimensions=video` over channel history) |
| Avg duration | Analytics `averageViewDuration`, all-time |
| Avg % viewed | Analytics `averageViewPercentage`, all-time |
| Impressions | Reporting API `video_thumbnail_impressions` (cumulative, live) |
| CTR | Reporting API `video_thumbnail_impressions_ctr` (cumulative, live) |

Impressions/CTR show **live** where the reach job has data, otherwise **n/a**
until it does (see below). They're cumulative across all reach data collected and
grow daily.

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

**Fully automated — no manual step.**

- Report type: **`channel_reach_basic_a1`**
  - Dimensions: `date`, `channel_id`, `video_id`
  - Metrics: `video_thumbnail_impressions`, `video_thumbnail_impressions_ctr`
- The fetch script lists reporting jobs, finds the one for this report type, and
  **creates it if missing** (`name: gcore-dashboard-reach`). It then downloads the
  daily report CSVs, parses the header to locate the columns (no hard-coded
  positions), and bakes per (video, day): **impressions** and **clicks**
  (clicks = impressions × CTR, with the CTR fraction/percent unit auto-detected).
  The Top Videos table shows each video's **cumulative** CTR = Σclicks ÷ Σimpressions.
- **Timing:** the Reporting API is job-based — data only starts **~24–48h after
  the job is created** and provides **~30 days** of history to begin with, then a
  new day is added every day. Older dates show **n/a** until they fill in.
- **Prerequisite (one-time):** the *YouTube Reporting API* must be enabled on the
  OAuth app's Google Cloud project. Same `yt-analytics.readonly` scope already used
  by the Analytics API, so the token is unchanged. If it isn't enabled, the build
  still succeeds and the on-page job card says so.

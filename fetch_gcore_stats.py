#!/usr/bin/env python3
"""Fetch Gcore YouTube stats -> one granular JSON blob the static page slices client-side.

Local run:  reads the MCP token at ~/.youtube-mcp-gcore/token.json
CI run:     set GCORE_TOKEN_JSON env var to the same token JSON
            (stored as a GitHub Actions secret).

Data sources (all on the SAME Gcore OAuth token — auth is untouched):
  * YouTube Data API v3        -> channel snapshot + per-video metadata
  * YouTube Analytics API v2   -> day-granular metrics (channel + per video)
  * YouTube Reporting API v1    -> reach reports (thumbnail impressions + CTR)

Why "granular": the page is a static GitHub-Pages site, so the browser can't
call the API live. Instead we bake day-level rows once per day and the page
aggregates whatever date range the user picks entirely client-side.

Output: writes JSON to argv[1] (default: docs/data.json).
"""
import json, os, sys, csv, io, gzip, urllib.request, urllib.parse, urllib.error, datetime

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "docs", "data.json")

# ---- tunables -------------------------------------------------------------
GRANULAR_DAYS = 365   # per-video / traffic / content day-level history baked in
TOP_N_TRACK   = 50    # videos we pull a per-day series for (drives range re-ranking)
REACH_TYPE    = "channel_reach_basic_a1"          # thumbnail impressions + CTR
REACH_TYPE_COMBINED = "channel_reach_combined_a1"  # richer variant (we prefer basic)
MAX_REACH_REPORTS = 120   # daily report files to download (backfill is ~30d anyway)


# ===========================================================================
# AUTH  — kept exactly as the original tool. DO NOT change the token flow.
# ===========================================================================
def load_token():
    env = os.environ.get("GCORE_TOKEN_JSON")
    if env:
        return json.loads(env)
    for p in [os.path.expanduser("~/.youtube-mcp-gcore/token.json")]:
        if os.path.exists(p):
            return json.load(open(p))
    sys.exit("No gcore token found (set GCORE_TOKEN_JSON or place ~/.youtube-mcp-gcore/token.json)")


D = load_token()


def access_token():
    body = urllib.parse.urlencode({
        'client_id': D['client_id'], 'client_secret': D['client_secret'],
        'refresh_token': D['refresh_token'], 'grant_type': 'refresh_token'}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request(D['token_uri'], data=body)).read())['access_token']


AT = access_token(); H = {'Authorization': 'Bearer ' + AT}


def data(path):
    return json.loads(urllib.request.urlopen(urllib.request.Request('https://www.googleapis.com/youtube/v3/' + path, headers=H)).read())


def ya(metrics, **kw):
    p = {'ids': 'channel==MINE', 'metrics': metrics, 'accessToken': AT}; p.update(kw)
    url = 'https://youtubeanalytics.googleapis.com/v2/reports?' + urllib.parse.urlencode(p)
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H)).read())
    except urllib.error.HTTPError as e:
        return {'ERR': e.code, 'b': e.read().decode()[:300]}


def ya_rows(metrics, **kw):
    """ya() but always returns a list of rows (never raises, never None)."""
    r = ya(metrics, **kw)
    if isinstance(r, dict) and r.get('ERR'):
        sys.stderr.write(f"  ! analytics {metrics} {kw.get('dimensions','')} -> {r['ERR']} {r.get('b','')[:120]}\n")
        return []
    return r.get('rows') or []


# ===========================================================================
# YouTube Reporting API helpers (same Bearer token / scope as Analytics)
# ===========================================================================
REPORTING = 'https://youtubereporting.googleapis.com/v1/'


def yr_get(path):
    return json.loads(urllib.request.urlopen(urllib.request.Request(REPORTING + path, headers=H)).read())


def yr_post(path, body):
    req = urllib.request.Request(REPORTING + path, data=json.dumps(body).encode(),
                                 headers={**H, 'Content-Type': 'application/json'}, method='POST')
    return json.loads(urllib.request.urlopen(req).read())


def yr_download(url):
    """Download a report file; transparently gunzip if needed; return text."""
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=H)).read()
    if raw[:2] == b'\x1f\x8b':            # gzip magic
        raw = gzip.decompress(raw)
    return raw.decode('utf-8', 'replace')


def find_col(header, *needles_groups):
    """Return the index of the first header cell matching ALL needles in any group."""
    low = [h.lower() for h in header]
    for group in needles_groups:
        for i, h in enumerate(low):
            if all(n in h for n in group):
                return i
    return None


# ===========================================================================
# Date helpers
# ===========================================================================
TODAY = datetime.date.today()


def iso(d):
    return d.isoformat()


def day_chunks(start, end, size=365):
    cur = start
    while cur <= end:
        ce = min(end, cur + datetime.timedelta(days=size - 1))
        yield cur, ce
        cur = ce + datetime.timedelta(days=1)


# ===========================================================================
# 1) Channel snapshot (lifetime, from the Data API)
# ===========================================================================
ch = data('channels?part=snippet,statistics,contentDetails&mine=true')['items'][0]
uploads_playlist = ch.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
created = datetime.date.fromisoformat(ch['snippet']['publishedAt'][:10])
snapshot = {
    'title': ch['snippet']['title'], 'id': ch['id'],
    'avatar': ch['snippet'].get('thumbnails', {}).get('high', {}).get('url'),
    'subs': int(ch['statistics'].get('subscriberCount', 0)),
    'total_views': int(ch['statistics'].get('viewCount', 0)),
    'videos': int(ch['statistics'].get('videoCount', 0)),
    'created': ch['snippet']['publishedAt']}
sys.stderr.write(f"Channel: {snapshot['title']} created {created} subs={snapshot['subs']}\n")

out = {
    'fetched': iso(TODAY),
    'today': iso(TODAY),                 # anchor for relative presets (data is static)
    'granular_days': GRANULAR_DAYS,
    'snapshot': snapshot,
}

# Shared granular day axis (per-video + reach reference into this by index)
gran_start = TODAY - datetime.timedelta(days=GRANULAR_DAYS - 1)
gran_days = [iso(gran_start + datetime.timedelta(days=i)) for i in range(GRANULAR_DAYS)]
gran_idx = {d: i for i, d in enumerate(gran_days)}
out['gran_days'] = gran_days

# ===========================================================================
# 2) Channel daily series — FULL history (drives overview cards + daily table
#    for ANY range incl. all-time). One row/day, so cheap. Chunked by year.
#    row = [date, views, minutes, avgDur, subsGained, subsLost, likes, comments, shares]
# ===========================================================================
DAILY_METRICS = 'views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares'
daily = []
for cs, ce in day_chunks(created, TODAY, 365):
    daily += ya_rows(DAILY_METRICS, dimensions='day', sort='day', startDate=iso(cs), endDate=iso(ce))
out['daily'] = daily
out['daily_cols'] = ['date', 'views', 'minutes', 'avgDur', 'subsGained', 'subsLost', 'likes', 'comments', 'shares']
sys.stderr.write(f"Channel daily rows: {len(daily)} ({daily[0][0] if daily else '-'} .. {daily[-1][0] if daily else '-'})\n")

# ===========================================================================
# 3) Per-video data
#    a) all-time per-video table (drives the "all-time" preset + out-of-window fallback)
#    b) per-video DAILY series for the granular window (drives exact range re-ranking)
# ===========================================================================
VID_METRICS = 'views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage'
all_top = ya_rows(VID_METRICS, dimensions='video', sort='-views', maxResults=200,
                  startDate=iso(created), endDate=iso(TODAY))
win_top = ya_rows('views', dimensions='video', sort='-views', maxResults=TOP_N_TRACK,
                  startDate=iso(gran_start), endDate=iso(TODAY))

# tracked set = top videos in the window UNION the all-time leaders (so both
# "last 7d" and "all-time" tables stay populated), capped for quota sanity.
track_ids = list(dict.fromkeys([r[0] for r in win_top] + [r[0] for r in all_top[:25]]))[:TOP_N_TRACK]

out['top_all_time'] = [{'id': r[0], 'views': r[1], 'minutes': r[2], 'avgDur': r[3],
                        'avgPct': round(r[4], 1)} for r in all_top]

video_daily = {}
for n, vid in enumerate(track_ids, 1):
    rows = ya_rows(VID_METRICS, dimensions='day', filters='video==' + vid, sort='day',
                   startDate=iso(gran_start), endDate=iso(TODAY))
    if not rows:
        continue
    I, V, W, AD, AP = [], [], [], [], []
    for r in rows:
        idx = gran_idx.get(r[0])
        if idx is None:
            continue
        I.append(idx); V.append(r[1]); W.append(r[2]); AD.append(r[3]); AP.append(round(r[4], 1))
    if I:
        video_daily[vid] = {'i': I, 'v': V, 'w': W, 'ad': AD, 'ap': AP}
out['video_daily'] = video_daily
sys.stderr.write(f"Tracked videos with daily series: {len(video_daily)}/{len(track_ids)}\n")

# ===========================================================================
# 4) Video metadata (titles, durations, lifetime counts).
#    Pull the FULL uploads catalog so even videos published in the last few days
#    (no Analytics data yet) appear — needed for publish-date filtering. Falls
#    back to just the referenced ids if the uploads playlist can't be listed.
# ===========================================================================
catalog_ids = []
if uploads_playlist:
    try:
        page = None
        while True:
            url = ('playlistItems?part=contentDetails&maxResults=50&playlistId=' + uploads_playlist
                   + (('&pageToken=' + page) if page else ''))
            r = data(url)
            catalog_ids += [it['contentDetails']['videoId'] for it in r.get('items', [])]
            page = r.get('nextPageToken')
            if not page:
                break
    except Exception as e:
        sys.stderr.write(f"  ! uploads catalog list failed: {e}\n")
need_ids = list(dict.fromkeys(catalog_ids + track_ids + [v['id'] for v in out['top_all_time']]))
sys.stderr.write(f"Catalog: {len(catalog_ids)} uploads, {len(need_ids)} ids to fetch metadata for\n")
meta = {}
for i in range(0, len(need_ids), 50):
    batch = need_ids[i:i + 50]
    vr = data('videos?part=snippet,contentDetails,statistics&id=' + ','.join(batch))
    for it in vr.get('items', []):
        st = it.get('statistics', {})
        meta[it['id']] = {'title': it['snippet']['title'], 'dur': it['contentDetails']['duration'],
                          'published': it['snippet']['publishedAt'][:10],
                          'lifetime_views': int(st.get('viewCount', 0)),
                          'lifetime_likes': int(st.get('likeCount', 0))}
out['videos'] = meta

# ===========================================================================
# 5) Traffic + content-type — EXACT per-day (few distinct keys, chunked quarterly
#    so we never hit row caps). row = [dayIndex, key, views, minutes]
# ===========================================================================
def dist_daily(dim, keep=None):
    out_rows = []
    for cs, ce in day_chunks(gran_start, TODAY, 90):
        for r in ya_rows('views,estimatedMinutesWatched', dimensions='day,' + dim, sort='day',
                         maxResults=2000, startDate=iso(cs), endDate=iso(ce)):
            idx = gran_idx.get(r[0])
            if idx is None or (keep and r[1] not in keep):
                continue
            out_rows.append([idx, r[1], r[2], r[3]])
    return out_rows


out['traffic_daily'] = dist_daily('insightTrafficSourceType')
out['content_daily'] = dist_daily('creatorContentType')

# ===========================================================================
# 6) Geography + demographics — pre-aggregated at preset windows.
#    Geo has ~200 countries (per-day would blow row caps) and demographics
#    (viewerPercentage) CANNOT combine with the day dimension at all, so both
#    are baked per preset window; the client picks the nearest window for a
#    custom range and labels it.  geo row=[country,views,minutes]; demo=[age,gender,pct]
# ===========================================================================
WINDOWS = [('7', 7), ('28', 28), ('90', 90), ('365', 365)]
geo_by_window, demo_by_window = {}, {}
for name, days in WINDOWS:
    s = iso(TODAY - datetime.timedelta(days=days - 1))
    geo_by_window[name] = ya_rows('views,estimatedMinutesWatched', dimensions='country', sort='-views',
                                  maxResults=15, startDate=s, endDate=iso(TODAY))
    demo_by_window[name] = ya_rows('viewerPercentage', dimensions='ageGroup,gender', sort='-viewerPercentage',
                                   startDate=s, endDate=iso(TODAY))
geo_by_window['all'] = ya_rows('views,estimatedMinutesWatched', dimensions='country', sort='-views',
                               maxResults=15, startDate=iso(created), endDate=iso(TODAY))
demo_by_window['all'] = ya_rows('viewerPercentage', dimensions='ageGroup,gender', sort='-viewerPercentage',
                                startDate=iso(created), endDate=iso(TODAY))
out['geo_by_window'] = geo_by_window
out['demo_by_window'] = demo_by_window

# ===========================================================================
# 7) Reach reports (thumbnail impressions + CTR) via the Reporting API.
#    Job-based: check for an existing job, else create one. Then download the
#    daily CSVs and bake per (video, day) impressions + clicks.
#    Degrades gracefully — never breaks the rest of the pipeline.
# ===========================================================================
def setup_reach():
    info = {'report_type': REACH_TYPE, 'api_enabled': True, 'exists': False, 'created_now': False,
            'job_id': None, 'create_time': None, 'reports': 0, 'dates': None,
            'first_data_expected': None, 'error': None}
    rows = []  # [(date, video_id, impressions, ctr_raw)]
    try:
        jobs = yr_get('jobs').get('jobs', [])
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        info['error'] = f'list jobs HTTP {e.code}: {body}'
        if e.code == 403 and ('disabled' in body.lower() or 'not been used' in body.lower()):
            info['api_enabled'] = False
            info['first_data_expected'] = 'Reporting API not enabled for this Cloud project — enable it once.'
        sys.stderr.write(f"  ! reach list jobs: {info['error']}\n")
        return info, rows

    job = next((j for j in jobs if j.get('reportTypeId') == REACH_TYPE), None)
    if not job:
        try:
            job = yr_post('jobs', {'reportTypeId': REACH_TYPE, 'name': 'gcore-dashboard-reach'})
            info['created_now'] = True
            sys.stderr.write(f"  + created reach job {job.get('id')}\n")
        except urllib.error.HTTPError as e:
            info['error'] = f'create job HTTP {e.code}: {e.read().decode()[:300]}'
            sys.stderr.write(f"  ! reach create job: {info['error']}\n")
            return info, rows
    info['exists'] = True
    info['job_id'] = job.get('id')
    info['create_time'] = job.get('createTime')

    # list reports for this job (paginated)
    reports, page = [], None
    try:
        while True:
            q = 'jobs/%s/reports?pageSize=100' % info['job_id'] + (('&pageToken=' + page) if page else '')
            r = yr_get(q)
            reports += r.get('reports', [])
            page = r.get('nextPageToken')
            if not page:
                break
    except urllib.error.HTTPError as e:
        info['error'] = f'list reports HTTP {e.code}: {e.read().decode()[:200]}'

    info['reports'] = len(reports)
    if not reports:
        # No data yet. New jobs backfill ~24-48h; ~30 days max history.
        base = info['create_time'] or iso(TODAY)
        try:
            cd = datetime.date.fromisoformat(base[:10])
        except ValueError:
            cd = TODAY
        info['first_data_expected'] = iso(cd + datetime.timedelta(days=2)) + ' (≈24-48h after job creation)'
        return info, rows

    # newest report per data-date wins -> process oldest first, let newer overwrite
    reports.sort(key=lambda x: x.get('createTime', ''))
    per = {}  # (date, video) -> (impressions, ctr_raw)
    for rep in reports[-MAX_REACH_REPORTS:]:
        url = rep.get('downloadUrl')
        if not url:
            continue
        try:
            text = yr_download(url)
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"  ! reach download {e.code}\n")
            continue
        rdr = csv.reader(io.StringIO(text))
        try:
            header = next(rdr)
        except StopIteration:
            continue
        low = [h.lower() for h in header]
        ci_date = next((i for i, h in enumerate(low) if 'date' in h), None)
        ci_vid = next((i for i, h in enumerate(low) if 'video_id' in h or ('video' in h and 'id' in h)), None)
        # CTR first, then impressions = an 'impression' column that ISN'T the CTR one
        ci_ctr = next((i for i, h in enumerate(low)
                       if 'ctr' in h or 'click_through' in h or 'click-through' in h or 'click' in h), None)
        ci_imp = next((i for i, h in enumerate(low) if 'impression' in h and i != ci_ctr), None)
        if None in (ci_date, ci_vid, ci_imp):
            sys.stderr.write(f"  ! reach header unrecognised: {header}\n")
            continue
        for row in rdr:
            if len(row) <= max(ci_date, ci_vid, ci_imp):
                continue
            d = row[ci_date]
            # report date is YYYYMMDD or YYYY-MM-DD
            if len(d) == 8 and d.isdigit():
                d = f'{d[:4]}-{d[4:6]}-{d[6:]}'
            try:
                imp = int(float(row[ci_imp] or 0))
            except ValueError:
                imp = 0
            ctr = 0.0
            if ci_ctr is not None and ci_ctr < len(row):
                try:
                    ctr = float(row[ci_ctr] or 0)
                except ValueError:
                    ctr = 0.0
            per[(d, row[ci_vid])] = (imp, ctr)
    rows = [(d, v, imp, ctr) for (d, v), (imp, ctr) in per.items()]
    if rows:
        ds = sorted({d for d, _, _, _ in rows})
        info['dates'] = [ds[0], ds[-1]]
        info['first_data_expected'] = 'available'
    return info, rows


reach_job, reach_rows = {'report_type': REACH_TYPE, 'error': 'skipped'}, []
try:
    reach_job, reach_rows = setup_reach()
except Exception as e:  # never let reach break the build
    reach_job = {'report_type': REACH_TYPE, 'error': f'{type(e).__name__}: {e}'}
    sys.stderr.write(f"  ! reach setup crashed: {e}\n")

# Decide CTR unit ONCE for the whole dataset (docs say %, but some CSVs use a
# 0-1 fraction). If virtually all values are <=1 treat as fraction. Then store
# impressions + derived clicks so the client computes range CTR unit-safely.
ctr_vals = [c for _, _, _, c in reach_rows if c]
as_fraction = bool(ctr_vals) and (sorted(ctr_vals)[int(len(ctr_vals) * 0.95)] <= 1.0)
reach_daily = []   # [dayIndex, video_id, impressions, clicks]
for d, v, imp, ctr in reach_rows:
    idx = gran_idx.get(d)
    if idx is None:
        continue
    frac = ctr if as_fraction else ctr / 100.0
    reach_daily.append([idx, v, imp, round(imp * frac, 2)])
reach_job['ctr_unit'] = 'fraction' if as_fraction else 'percent'
out['reach_daily'] = reach_daily
out['reach_job'] = reach_job
sys.stderr.write(f"Reach: job={reach_job.get('job_id')} exists={reach_job.get('exists')} "
                 f"created_now={reach_job.get('created_now')} rows={len(reach_daily)} "
                 f"expected={reach_job.get('first_data_expected')}\n")

# ===========================================================================
# Write
# ===========================================================================
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w').write(json.dumps(out, separators=(',', ':')))
sys.stderr.write(f"\nWrote {OUT} ({os.path.getsize(OUT)//1024} KB)\n")
print(json.dumps({k: (f'<{len(v)} rows>' if isinstance(v, list) else
                       (f'<{len(v)} keys>' if isinstance(v, dict) else v))
                  for k, v in out.items()}, indent=1))

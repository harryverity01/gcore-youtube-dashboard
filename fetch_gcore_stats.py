#!/usr/bin/env python3
"""Fetch Gcore YouTube stats (Data + Analytics API) -> clean JSON blob.

Local run:  reads the MCP token at ~/.youtube-mcp-gcore/token.json
CI run:     set GCORE_TOKEN_JSON env var to the same token JSON
            (stored as a GitHub Actions secret).

Output: writes JSON to the path in argv[1] (default: docs/data.json) and
        also prints it to stdout.
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error, datetime

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "docs", "data.json")


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


end = datetime.date.today(); start = end - datetime.timedelta(days=27)
sd, ed = start.isoformat(), end.isoformat()
prev_end = start - datetime.timedelta(days=1); prev_start = prev_end - datetime.timedelta(days=27)
psd, ped = prev_start.isoformat(), prev_end.isoformat()

out = {'fetched': end.isoformat(), 'window': [sd, ed], 'prev_window': [psd, ped]}

ch = data('channels?part=snippet,statistics&mine=true')['items'][0]
out['snapshot'] = {
    'title': ch['snippet']['title'], 'id': ch['id'],
    'avatar': ch['snippet'].get('thumbnails', {}).get('high', {}).get('url'),
    'subs': int(ch['statistics'].get('subscriberCount', 0)),
    'total_views': int(ch['statistics'].get('viewCount', 0)),
    'videos': int(ch['statistics'].get('videoCount', 0)),
    'created': ch['snippet']['publishedAt']}

OVERVIEW_METRICS = 'views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares'
out['overview'] = ya(OVERVIEW_METRICS, startDate=sd, endDate=ed).get('rows')
out['overview_prev'] = ya(OVERVIEW_METRICS, startDate=psd, endDate=ped).get('rows')
out['by_content'] = ya('views,estimatedMinutesWatched,averageViewDuration,likes', dimensions='creatorContentType', startDate=sd, endDate=ed).get('rows')
out['traffic'] = ya('views,estimatedMinutesWatched', dimensions='insightTrafficSourceType', sort='-views', startDate=sd, endDate=ed).get('rows')
out['demographics'] = ya('viewerPercentage', dimensions='ageGroup,gender', sort='-viewerPercentage', startDate=sd, endDate=ed).get('rows')
out['geography'] = ya('views,estimatedMinutesWatched', dimensions='country', sort='-views', maxResults=12, startDate=sd, endDate=ed).get('rows')
out['day_of_week'] = ya('views', dimensions='day', startDate=sd, endDate=ed).get('rows')
# Daily trend series for the 28-day window (drives the line chart)
out['daily'] = ya('views,estimatedMinutesWatched,subscribersGained', dimensions='day', sort='day', startDate=sd, endDate=ed).get('rows')

# Top videos by views (all content), resolve titles + durations + published date
tv = ya('views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares', dimensions='video', sort='-views', maxResults=25, startDate=sd, endDate=ed).get('rows') or []
ids = [r[0] for r in tv]
meta = {}
for i in range(0, len(ids), 50):
    batch = ids[i:i + 50]
    vr = data('videos?part=snippet,contentDetails,statistics&id=' + ','.join(batch))
    for it in vr['items']:
        meta[it['id']] = {'title': it['snippet']['title'], 'dur': it['contentDetails']['duration'],
                          'published': it['snippet']['publishedAt'][:10]}
out['top_videos'] = [{'id': r[0], 'views': r[1], 'watch_min': r[2], 'avg_dur': r[3], 'likes': r[4],
                      'comments': r[5], 'shares': r[6], **meta.get(r[0], {})} for r in tv]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w').write(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
sys.stderr.write(f"\nWrote {OUT}\n")

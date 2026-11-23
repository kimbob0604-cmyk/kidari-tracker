"""tracker.db + data/*.json + raw/ → docs/index.html (탭형 대시보드, GitHub Pages)."""
import sqlite3, os, json, glob, datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(BASE, 'tracker.db'))
KST = dt.timezone(dt.timedelta(hours=9))
LAUNCH = dt.date(2026, 10, 19)


def P(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).replace(tzinfo=None)


def tslist(sql, args=()):
    return [r[0] for r in c.execute(sql, args)]


def prev_ts(ts, hours):
    last = P(ts[-1])
    for t in reversed(ts[:-1]):
        if (last - P(t)).total_seconds() / 3600 >= hours:
            return t
    return None


def hrs(a, b):
    return (P(b) - P(a)).total_seconds() / 3600


def latest_raw(name):
    f = sorted(glob.glob(os.path.join(BASE, 'raw', '*', name)))
    return json.load(open(f[-1])) if f else None


# ---------- 티즈
tz = tslist('select distinct ts from teaz order by ts')
T = {}
for r in c.execute('select ts,char_id,name,genre,work_id,created,messages,likes from teaz'):
    T.setdefault(r[0], {})[r[1]] = r
last = tz[-1]; p1 = prev_ts(tz, 6); p7 = prev_ts(tz, 24 * 6.5)
raw_t = {x['id']: x for x in (latest_raw('teaz.json') or [])}
lz_kr_raw = latest_raw('lezhin_kr.json') or {'data': []}
alias_rank = {x.get('alias'): x.get('currentRank') for x in lz_kr_raw['data']}
chars = []
for k, r in T[last].items():
    x = raw_t.get(k, {})
    pub = max(P(r[5]).date() if r[5] else LAUNCH, LAUNCH)
    age = max((P(last).date() - pub).days, 1)
    links = x.get('platform_links') or []
    lz_alias = next((l['url'].rstrip('/').split('/')[-1] for l in links if l.get('platform') == 'lezhin'), None)
    chars.append(dict(
        id=k, name=r[2], genre=r[3], msgs=r[6], likes=r[7], pub=str(pub), age=age, avg=r[6] / age,
        d1=(r[6] - T[p1][k][6]) * 24 / hrs(p1, last) if p1 and k in T[p1] else None,
        d7=(r[6] - T[p7][k][6]) if p7 and k in T[p7] else None,
        img=(x.get('avatar_url') or '').replace('portrait-960', 'portrait-640') or None,
        tagline=x.get('tagline'), work=x.get('source_work_title'), platform=x.get('source_platform'),
        lz_rank=alias_rank.get(lz_alias), url=f"https://myteaz.io/chat/r/{x.get('room_public_id')}" if x.get('room_public_id') else None))
series = [(t, sum(v[6] or 0 for v in T[t].values())) for t in tz]
daily = [(b[0], (b[1] - a[1]) * 24 / hrs(a[0], b[0])) for a, b in zip(series[:-1], series[1:]) if hrs(a[0], b[0]) >= 6]
cum = series[-1][1]; days = (P(last).date() - LAUNCH).days
basis = daily[-1][1] if daily else cum / days
# 공개일 기준 누적 경로(추정): 캐릭터별 공개일부터 일정 속도 가정 → 출시 후 누적 곡선 재구성
recon = []
d0 = LAUNCH
while d0 <= P(last).date():
    recon.append((str(d0), sum(ch['msgs'] * min(max((d0 - dt.date.fromisoformat(ch['pub'])).days, 0) / ch['age'], 1) for ch in chars)))
    d0 += dt.timedelta(days=1)


# ---------- 레진 KR/US
def lezhin(cc):
    ts = tslist('select distinct ts from lezhin where country=? order by ts', (cc,))
    D = {}
    for r in c.execute('select ts,content_id,title,genre,rank,views,subs from lezhin where country=?', (cc,)):
        D.setdefault(r[0], {})[r[1]] = r
    lt = ts[-1]; p = prev_ts(ts, 6); h = hrs(p, lt) if p else None
    raw = latest_raw(f'lezhin_{cc}.json') or {'data': []}
    alias = {str(x['id']): x.get('alias') for x in raw['data']}
    items = []
    for k, r in D[lt].items():
        pr = D[p].get(k) if p else None
        items.append(dict(id=k, title=r[2], genre=r[3], rank=r[4], views=r[5], subs=r[6],
                          dv=(r[5] - pr[5]) * 24 / h if pr else None, ds=(r[6] - pr[6]) * 24 / h if pr else None,
                          drank=(pr[4] - r[4]) if pr else None,
                          img=f'https://ccdn.lezhin.com/v2/comics/{k}/images/thumbnails/1.webp',
                          url=f"https://www.lezhin.com/{'ko' if cc == 'kr' else 'en'}/comic/{alias.get(k)}" if alias.get(k) else None))
    ser = [(t, sum(v[5] or 0 for v in D[t].values())) for t in ts]
    tdv = sum(x['dv'] for x in items if x['dv'] is not None) if p else None
    tds = sum(x['ds'] for x in items if x['ds'] is not None) if p else None
    return dict(items=items, series=ser, dv=tdv, ds=tds)


def ranking(src, prefix):
    ts = tslist('select distinct ts from rankings where source=? order by ts', (src,))
    if not ts:
        return dict(items=[])
    D = {}
    for r in c.execute('select ts,item_id,title,genre,rank,img,change from rankings where source=?', (src,)):
        D.setdefault(r[0], {})[r[1]] = r
    lt = ts[-1]; p = prev_ts(ts, 6)
    items = []
    for k, r in D[lt].items():
        pr = D[p].get(k) if p else None
        items.append(dict(id=k, title=r[2], genre=r[3], rank=r[4], img=r[5], change=r[6], drank=(pr[4] - r[4]) if pr else None,
                          url=prefix + k if prefix else None))
    return dict(items=items, n=len(ts))


# ---------- 앱
pn = {'com.lezhin.comics': ('레진코믹스', 'KR'), 'com.bomcomics.bomtoon.playstore': ('봄툰', 'KR'), 'com.lezhin.snack': ('레진스낵', 'KR'),
      'com.balcony.boomtoon': ('LEZHIN TH', 'TH'), 'com.balcony.bomtoon.tw': ('BOMTOON TW', 'TW'), 'balcony.beltoon.jp': ('BeLTOON JP', 'JP'),
      'com.delitoon': ('DELITOON FR', 'FR'), 'de.delitoon': ('DELITOON DE', 'DE')}
pts = tslist('select distinct ts from play order by ts')
PD = {}
for r in c.execute('select ts,pkg,installs,rating_count,rating from play'):
    PD.setdefault(r[0], {})[r[1]] = r
pp = prev_ts(pts, 6)
apps = []
for k, r in PD[pts[-1]].items():
    pr = PD[pp].get(k) if pp else None
    apps.append(dict(name=pn.get(k, (k, ''))[0], country=pn.get(k, ('', '?'))[1], pkg=k, installs=r[2], rc=r[3], rating=r[4],
                     d=(r[2] - pr[2]) * 24 / hrs(pp, pts[-1]) if pr and r[2] and pr[2] else None))
ast = [dict(country=r[0], name=r[1], rc=r[2], rating=r[3]) for r in c.execute(
    'select country,name,rating_count,rating from appstore where ts=(select max(ts) from appstore)')]

payload = dict(
    generated=dt.datetime.now(KST).strftime('%Y-%m-%d %H:%M'), last=last, nsnap=len(tz), first=tz[0],
    teaz=dict(chars=chars, series=series, daily=daily, recon=recon, cum=cum, days=days, basis=basis,
              basis_label='직전 24h 환산' if daily else f'출시 후 {days}일 평균'),
    lezhin=dict(kr=lezhin('kr'), us=lezhin('us'), jp=ranking('lezhin_jp', 'https://lezhin.jp/comic/')),
    snack=ranking('snack', None), apps=apps, appstore=ast,
    fin=json.load(open(os.path.join(BASE, 'data', 'finance.json'))),
    price=json.load(open(os.path.join(BASE, 'data', 'price.json'))),
    topco=json.load(open(os.path.join(BASE, 'benchmark', 'toptoonchat.json'))),
    topco_thumbs=json.load(open(os.path.join(BASE, 'benchmark', 'topco_thumbs.json'))) if os.path.exists(os.path.join(BASE, 'benchmark', 'topco_thumbs.json')) else {},
    runs=[dict(ts=r[0], src=r[1], ok=r[2], note=r[3]) for r in c.execute('select * from runs order by ts desc limit 30')],
)
tpl = open(os.path.join(BASE, 'template.html'), encoding='utf-8').read()
out = tpl.replace('/*__DATA__*/null', json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
os.makedirs(os.path.join(BASE, 'docs'), exist_ok=True)
open(os.path.join(BASE, 'docs', 'index.html'), 'w', encoding='utf-8').write(out)
print('built', len(out) // 1024, 'KB · teaz basis', round(basis), '· snaps', len(tz))

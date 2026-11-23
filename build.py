"""tracker.db → docs/index.html (키다리스튜디오 대체데이터 일일 트래커, GitHub Pages)."""
import sqlite3, os, json, html, datetime as dt
from calc_section import calc_html
BASE = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(BASE, 'tracker.db'))
LAUNCH = dt.date(2026, 10, 19)          # 티즈 출시일
PRICE = (40, 50)                        # 턴당 과금(원), 9/30 탐방
SCEN = [('Bear', 30), ('Base', 85), ('회사 Base', 165)]  # 2027E 티즈 매출(억원)


def P(s): return dt.datetime.fromisoformat(s)
def f0(v): return '—' if v is None else f'{v:,.0f}'
def f1(v): return '—' if v is None else f'{v:,.1f}'
def sg(v, f=f0): return '—' if v is None else (('+' if v > 0 else '') + f(v))
def esc(s): return html.escape(str(s or ''))


snaps = [r[0] for r in c.execute('select distinct ts from teaz order by ts')]


def per_snap(q, key=lambda r: r[0]):
    out = {}
    for r in c.execute(q):
        out.setdefault(r[0], {})[r[1]] = r[2:]
    return out


teaz = per_snap('select ts,char_id,name,genre,created,messages,likes from teaz')
lez = {}
for r in c.execute('select ts,country,content_id,title,genre,rank,views,subs from lezhin'):
    lez.setdefault((r[0], r[1]), {})[r[2]] = r[3:]
play = per_snap('select ts,pkg,installs,rating_count,rating from play')
appst = {}
for r in c.execute('select ts,country,track_id,name,rating_count,rating from appstore'):
    appst.setdefault(r[0], {})[(r[1], r[2])] = r[3:]


def deltas(series, idx):
    """연속 스냅샷 간 증분(공통 키 합)과 24h 환산."""
    rows = []
    for a, b in zip(series[:-1], series[1:]):
        ta, da = a; tb, db = b
        common = set(da) & set(db)
        d = sum((db[k][idx] or 0) - (da[k][idx] or 0) for k in common)
        h = (P(tb) - P(ta)).total_seconds() / 3600
        rows.append((tb, d, h, d * 24 / h if h else None, len(set(db) - set(da))))
    return rows


# ---- 티즈
tser = [(t, teaz[t]) for t in snaps]
t_tot = [(t, sum(v[3] or 0 for v in d.values())) for t, d in tser]
t_del = deltas(tser, 3)
last_t, last_d = tser[-1]
cum = t_tot[-1][1]
days_since = (P(last_t).date() - LAUNCH).days
avg_day = cum / days_since if days_since else None
ok_del = [x for x in t_del if x[2] >= 6]
recent24 = ok_del[-1][3] if ok_del else None
basis = recent24 if recent24 is not None else avg_day
ann = [basis * p * 365 / 1e8 for p in PRICE] if basis else [None, None]

# 캐릭터 표
prev_d = tser[-2][1] if len(tser) > 1 else {}
wk = [x for x in tser if (P(last_t) - P(x[0])).days >= 7]
wk_d = wk[-1][1] if wk else {}
chars = []
for k, v in last_d.items():
    name, genre, created, msg, like = v
    d1 = msg - prev_d[k][3] if k in prev_d else None
    d7 = msg - wk_d[k][3] if k in wk_d else None
    chars.append((name, genre, created[:10] if created else '', msg, d1, d7, like))
chars.sort(key=lambda x: -x[3])
genre = {}
for v in last_d.values():
    genre[v[1]] = genre.get(v[1], 0) + (v[3] or 0)

# ---- 레진
def lz(country):
    ser = sorted([(t, d) for (t, cc), d in lez.items() if cc == country])
    tv = [(t, sum(v[3] or 0 for v in d.values())) for t, d in ser]
    dv = deltas(ser, 3); ds = deltas(ser, 4)
    lt, ld = ser[-1]
    pd = ser[-2][1] if len(ser) > 1 else {}
    top = sorted(ld.items(), key=lambda kv: kv[1][2] or 999)[:15]
    rows = []
    for k, v in top:
        title, g, rank, views, subs = v
        pr = pd.get(k)
        rows.append((rank, title, g, views, (views - pr[3]) if pr else None, subs, (pr[2] - rank) if pr else None))
    return dict(tv=tv, dv=dv, ds=ds, rows=rows, n=len(ld))


LZ = {cc: lz(cc) for cc in ('kr', 'us')}

# ---- 앱
pser = sorted(play.items())
pkgname = {'com.lezhin.comics': '레진코믹스', 'com.bomcomics.bomtoon.playstore': '봄툰', 'com.lezhin.snack': '레진스낵'}
apps = []
lt, ld = pser[-1]
pd = pser[-2][1] if len(pser) > 1 else {}
for k, v in ld.items():
    d = (v[0] - pd[k][0]) if k in pd and v[0] and pd[k][0] else None
    h = (P(lt) - P(pser[-2][0])).total_seconds() / 3600 if len(pser) > 1 else None
    apps.append((pkgname.get(k, k), v[0], d, d * 24 / h if d is not None and h else None, v[1], v[2]))


# ---- 탑코 벤치마크
TB = json.load(open(os.path.join(BASE, 'benchmark', 'toptoonchat.json')))
def mavg(region, m):
    v = [x for d, x in zip(TB['dates'], TB['regions'][region]['dS']) if d.startswith(m) and x is not None]
    return sum(v) / len(v) if v else None
sep, nov = mavg('ALL', '2026-09'), mavg('ALL', TB['dates'][-1][:7])
last = {r: TB['regions'][r]['cumS'][-1] for r in TB['regions']}
topco = dict(sep=sep, nov=nov, ovs=(last['JP'] + last['TW'] + last['GLOBAL']) / last['ALL'] * 100)
topco_ser = {r: list(zip(TB['dates'], TB['regions'][r]['dS'])) for r in ('KR', 'JP', 'TW', 'GLOBAL')}

# ---- SVG 라인
def svg(points, color='var(--accent)', unit='', w=560, h=180):
    pts = [(P(t), v) for t, v in points if v is not None]
    if len(pts) < 2:
        return f'<div class="empty">스냅샷 {len(pts)}개 · 2개 이상 쌓이면 추이가 그려짐</div>'
    xs = [p[0].timestamp() for p in pts]; ys = [p[1] for p in pts]
    lo, hi = min(ys), max(ys); lo = min(lo, 0) if lo >= 0 and hi > 0 and lo / hi < .3 else lo
    hi = hi if hi > lo else lo + 1
    L, R, T, B = 56, 12, 10, 26; pw, ph = w - L - R, h - T - B
    X = lambda x: L + (x - xs[0]) / ((xs[-1] - xs[0]) or 1) * pw
    Y = lambda y: T + ph - (y - lo) / (hi - lo) * ph
    path = ' '.join(f'{"M" if i == 0 else "L"}{X(x):.1f},{Y(y):.1f}' for i, (x, y) in enumerate(zip(xs, ys)))
    g = ''.join(f'<line x1="{L}" x2="{w-R}" y1="{Y(lo+(hi-lo)*i/4):.1f}" y2="{Y(lo+(hi-lo)*i/4):.1f}" class="grid"/>'
                f'<text x="{L-6}" y="{Y(lo+(hi-lo)*i/4)+4:.1f}" class="ax" text-anchor="end">{lo+(hi-lo)*i/4:,.0f}</text>' for i in range(5))
    xl = f'<text x="{L}" y="{h-6}" class="ax">{pts[0][0]:%m/%d}</text><text x="{w-R}" y="{h-6}" class="ax" text-anchor="end">{pts[-1][0]:%m/%d}</text>'
    dots = ''.join(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="2.5" fill="{color}"><title>{dt.datetime.fromtimestamp(x):%m/%d %H:%M} · {y:,.0f}{unit}</title></circle>' for x, y in zip(xs, ys))
    return f'<svg viewBox="0 0 {w} {h}" role="img">{g}<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>{dots}{xl}</svg>'


def table(head, rows, num=()):
    th = ''.join(f'<th class="{"n" if i in num else ""}">{esc(h)}</th>' for i, h in enumerate(head))
    tr = ''.join('<tr>' + ''.join(f'<td class="{"n" if i in num else ""}">{v}</td>' for i, v in enumerate(r)) + '</tr>' for r in rows)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def tile(lbl, val, sub):
    return f'<div class="tile"><div class="tl">{lbl}</div><div class="tv">{val}</div><div class="ts">{sub}</div></div>'


basis_lbl = '직전 24h 환산' if recent24 is not None else f'출시 후 {days_since}일 평균'
tiles = ''.join([
    tile('티즈 누적 메시지', f0(cum), f'캐릭터 {len(last_d)}명 · 출시 {days_since}일'),
    tile('티즈 하루 메시지', f0(basis), basis_lbl),
    tile('티즈 연환산 매출(상한)', f'{f1(ann[0])}~{f1(ann[1])}억', f'턴당 {PRICE[0]}~{PRICE[1]}원 × 365'),
    tile('레진 KR Top100 조회 증분', sg(LZ['kr']['dv'][-1][3]) if LZ['kr']['dv'] and LZ['kr']['dv'][-1][2] >= 6 else '—', '24h 환산 · 공통 작품'),
    tile('레진 US Top100 조회 증분', sg(LZ['us']['dv'][-1][3]) if LZ['us']['dv'] and LZ['us']['dv'][-1][2] >= 6 else '—', '24h 환산 · 공통 작품'),
])
scen = ''.join(f'<tr><td>{n}</td><td class="n">{v}억</td><td class="n">{v*1e8/365/PRICE[1]:,.0f}</td><td class="n">{(v*1e8/365/PRICE[1]/basis):,.0f}배</td></tr>' if basis else '' for n, v in SCEN)

chars_rows = [(esc(n), esc(g), d, f0(m), sg(d1), sg(d7), f0(l)) for n, g, d, m, d1, d7, l in chars]
genre_rows = [(esc(g), f0(v), f'{v/cum*100:.1f}%') for g, v in sorted(genre.items(), key=lambda x: -x[1])]


def lz_sec(cc, label):
    d = LZ[cc]
    rows = [(r[0], esc(r[1]), esc(r[2]), f0(r[3]), sg(r[4]), f0(r[5]), sg(r[6])) for r in d['rows']]
    return f'''<div class="card"><h2>레진코믹스 {label} · 실시간 Top{d["n"]}</h2>
<p class="cap">Top100 누적 조회수 합계 추이 (순위 밖으로 빠진 작품은 빠지므로 증분은 공통 작품 기준으로 별도 계산)</p>{svg(d["tv"])}
{table(["순위","작품","장르","누적 조회","직전 대비","구독","순위 변동"],rows,num=(0,3,4,5,6))}</div>'''


now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
doc = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>키다리 대체데이터 트래커</title><style>
:root{{--bg:#f3f6f9;--panel:#fff;--ink:#172033;--ink2:#475467;--ink3:#667085;--line:#d9e0e8;--grid:#e3e8ef;--accent:#1F3A93;--up:#b42318;--navy:#172b4d}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0d1420;--panel:#16202f;--ink:#eaf1fa;--ink2:#b3c3d6;--ink3:#8fa3ba;--line:#2a3a50;--grid:#243348;--accent:#69b0ff;--up:#ff7a70;--navy:#0a1322}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Pretendard","Apple SD Gothic Neo",system-ui,sans-serif;font-size:15px;line-height:1.55}}
header{{background:var(--navy);color:#fff;padding:20px 16px}}header h1{{margin:0;font-size:21px}}header p{{margin:4px 0 0;color:#c5d2e6;font-size:13px}}
main{{max-width:1180px;margin:0 auto;padding:16px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:14px}}
h2{{font-size:16px;margin:0 0 6px}}.cap{{color:var(--ink3);font-size:12.5px;margin:0 0 10px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-bottom:14px}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}.tl{{font-size:12.5px;color:var(--ink3)}}.tv{{font-size:24px;font-weight:700;color:var(--accent)}}.ts{{font-size:12px;color:var(--ink2)}}
.tw{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13.5px}}th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}th{{color:var(--ink3);font-weight:600}}.n{{text-align:right;font-variant-numeric:tabular-nums}}
svg{{width:100%;max-width:760px;height:auto}}.grid{{stroke:var(--grid)}}.ax{{fill:var(--ink3);font-size:11px}}.empty{{color:var(--ink3);font-size:13px;padding:18px 0}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 14px;margin-bottom:12px}}label{{font-size:12.5px;color:var(--ink2);display:flex;flex-direction:column;gap:3px}}input{{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-height:36px;width:100%}}.ct input{{max-width:110px;text-align:right}}td.d{{color:var(--ink3);font-size:12px;white-space:normal}}.bench{{background:var(--bg);border-radius:8px;padding:8px 10px;font-size:13px;margin-bottom:10px}}h3{{font-size:14px;margin:12px 0 4px}}button{{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer;min-height:40px}}
.two{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}ul{{margin:0;padding-left:18px}}li{{margin:3px 0}}
</style></head><body><header><h1>키다리스튜디오 대체데이터 일일 트래커</h1><p>스냅샷 {len(snaps)}회 · 최신 {last_t.replace("T"," ")} KST · 생성 {now}</p></header><main>
<div class="tiles">{tiles}</div>
<div class="card"><h2>티즈 매출로 잇기</h2><p class="cap">하루 메시지 × 턴당 {PRICE[0]}~{PRICE[1]}원 = 일 매출(상한). 2027E 시나리오가 요구하는 하루 턴수와 비교</p>
{table(["2027E 시나리오","티즈 매출","필요한 하루 턴(50원)","현재 대비"],[] ,num=(1,2,3)).replace("<tbody></tbody>","<tbody>"+scen+"</tbody>")}</div>
<div class="two"><div class="card"><h2>티즈 누적 메시지</h2><p class="cap">myteaz.io 공개 API · 캐릭터 message_count 합계</p>{svg(t_tot)}</div>
<div class="card"><h2>티즈 하루 메시지 (24h 환산)</h2><p class="cap">연속 스냅샷 증분 ÷ 경과시간 × 24</p>{svg([(t, d24) for t, d, h, d24, n in t_del])}</div></div>
<div class="card"><h2>티즈 캐릭터별</h2>{table(["캐릭터","장르","생성일","누적 메시지","직전 대비","7일","좋아요"],chars_rows,num=(3,4,5,6))}</div>
<div class="card"><h2>티즈 장르별 누적 메시지</h2>{table(["장르","누적","비중"],genre_rows,num=(1,2))}</div>
{lz_sec("kr","KR")}{lz_sec("us","US")}
<div class="card"><h2>앱 (구글플레이 KR)</h2>{table(["앱","설치수","직전 대비","24h 환산","평점 수","평점"],[(a, f0(b), sg(d), sg(e), f0(r), f'{s:.2f}' if s else "—") for a, b, d, e, r, s in apps],num=(1,2,3,4,5))}</div>
{calc_html(basis, topco)}
<div class="card"><h2>탑툰챗 벤치마크 (엔키AX)</h2><p class="cap">{esc(TB['source'])} · 스냅샷 {esc(TB['snapshot'])} · 하루 세션 증가(24h 환산). 세션 ≠ 티즈 메시지(단위 다름) → 추세 비교용</p>
<div class="two">{''.join(f'<div><b>{r}</b>{svg([(d+"T00:00:00", v) for d, v in topco_ser[r]], unit="건")}</div>' for r in ('KR','JP','TW','GLOBAL'))}</div></div>
<div class="card"><h2>정의와 한계</h2><ul>
<li><b>티즈 메시지</b> = 캐릭터별 message_count 합. AI 응답 포함 여부·무료 턴 비중은 미확인 → 매출 환산은 상한</li>
<li>7월 생성 캐릭터는 출시(10/19) 전 테스트 메시지가 섞였을 수 있음 → 출시 후 평균도 상한</li>
<li><b>레진 조회</b> = 작품 viewCount(누적). Top100 밖 작품은 잡히지 않음. 조회는 유료 결제가 아님 → 웹툰 매출의 방향성 지표</li>
<li><b>매출 연결</b>: 티즈 → 신사업(티즈) 매출 · 레진 KR 조회·구독 → 웹툰 국내 · 레진 US → 웹툰 해외(미국 2025 242억) · 설치수 → 플랫폼 저변</li>
<li>봄툰은 robots.txt가 API를 금지해 수집하지 않음. 레진 JP는 공개 API 미확인</li>
<li>수집: 하루 1회, 엔드포인트당 1회 호출(1.5초 간격). 원자료 raw/날짜/ 폴더 보관</li></ul></div>
</main></body></html>'''
os.makedirs(os.path.join(BASE, 'docs'), exist_ok=True)
open(os.path.join(BASE, 'docs', 'index.html'), 'w').write(doc)
print('dashboard.html', len(snaps), 'snaps', 'cum', cum, 'basis', basis, 'ann', ann)

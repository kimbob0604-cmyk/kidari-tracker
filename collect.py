"""키다리스튜디오 계열 공개 지표 일일 스냅샷 (티즈·레진 KR/US·구글플레이·앱스토어).
요청은 엔드포인트당 하루 1회(티즈는 페이지네이션 시 페이지당 1회), 요청 사이 1.5초 간격."""
import json, os, re, sqlite3, time, urllib.request, datetime as dt
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,'tracker.db')
UA={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}
KST=dt.timezone(dt.timedelta(hours=9))
def get(url,headers=None,raw=False):
    req=urllib.request.Request(url,headers={**UA,**(headers or {})})
    b=urllib.request.urlopen(req,timeout=30).read(); time.sleep(1.5)
    return b.decode('utf-8','ignore') if raw else json.loads(b)
def db():
    c=sqlite3.connect(DB)
    c.executescript('''
    create table if not exists teaz(ts text,char_id text,name text,genre text,work_id text,created text,messages int,likes int);
    create table if not exists lezhin(ts text,country text,content_id text,title text,genre text,rank int,views int,subs int);
    create table if not exists play(ts text,pkg text,installs int,rating_count int,rating real);
    create table if not exists appstore(ts text,country text,track_id int,name text,rating_count int,rating real);
    create table if not exists runs(ts text,source text,ok int,note text);''')
    return c
def main():
    ts=dt.datetime.now(KST).strftime('%Y-%m-%dT%H:%M:%S'); day=ts[:10]
    rawdir=os.path.join(BASE,'raw',day); os.makedirs(rawdir,exist_ok=True)
    c=db()
    def run(src,fn):
        try: n=fn(); c.execute('insert into runs values(?,?,?,?)',(ts,src,1,str(n)))
        except Exception as e: c.execute('insert into runs values(?,?,?,?)',(ts,src,0,repr(e)[:300]))
    def teaz():
        items=[]; cur=None
        for _ in range(20):
            d=get('https://api.myteaz.io/chat/characters'+(f'?cursor={cur}' if cur else ''))
            items+=d.get('items',[]); cur=d.get('next_cursor')
            if not cur: break
        json.dump(items,open(os.path.join(rawdir,'teaz.json'),'w'),ensure_ascii=False)
        for x in items:
            c.execute('insert into teaz values(?,?,?,?,?,?,?,?)',(ts,x.get('id'),x.get('name'),x.get('genre'),str(x.get('source_work_id')),x.get('created_at'),x.get('message_count'),x.get('like_count')))
        return len(items)
    def lezhin(country):
        d=get('https://api.lezhin.com/v2/content-list/ranking?rankType=realtime&filter=all&genres=&limit=100',{'x-lz-country':country,'x-lz-locale':{'kr':'ko-KR','us':'en-US'}[country]})
        json.dump(d,open(os.path.join(rawdir,f'lezhin_{country}.json'),'w'),ensure_ascii=False)
        for x in d['data']:
            c.execute('insert into lezhin values(?,?,?,?,?,?,?,?)',(ts,country,str(x['id']),x.get('title'),','.join(x.get('genres') or []),x.get('currentRank'),x.get('viewCount'),x.get('subscriptions')))
        return len(d['data'])
    def play():
        n=0
        for pkg in ['com.lezhin.comics','com.bomcomics.bomtoon.playstore','com.lezhin.snack']:
            t=get(f'https://play.google.com/store/apps/details?id={pkg}&hl=ko&gl=KR',raw=True)
            m=re.search(r'\["([\d,]+\+)",(\d+),(\d+),"[^"]*"\]',t) or re.search(r'\["([\d,]+\+)",\d*,?(\d+),(\d+)',t)
            r=re.search(r'"ratingValue":"([\d.]+)","ratingCount":"(\d+)"',t)
            c.execute('insert into play values(?,?,?,?,?)',(ts,pkg,int(m.group(3)) if m else None,int(r.group(2)) if r else None,float(r.group(1)) if r else None)); n+=1
        return n
    def appstore():
        n=0
        for cc in ['kr','us','jp']:
            d=get(f'https://itunes.apple.com/lookup?id=664973122,1041858138,6751880104&country={cc}')
            for x in d.get('results',[]):
                c.execute('insert into appstore values(?,?,?,?,?,?)',(ts,cc,x.get('trackId'),x.get('trackName'),x.get('userRatingCount'),x.get('averageUserRating'))); n+=1
        return n
    run('teaz',teaz); run('lezhin_kr',lambda:lezhin('kr')); run('lezhin_us',lambda:lezhin('us')); run('play',play); run('appstore',appstore)
    c.commit(); print(ts,[r for r in c.execute('select source,ok,note from runs where ts=?',(ts,))])
if __name__=='__main__': main()

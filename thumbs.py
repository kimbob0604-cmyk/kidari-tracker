"""탑툰챗 캐릭터 썸네일을 받아 200px JPEG로 줄여 docs/img/topco/{id}.jpg 저장(없는 것만)."""
import json, os, time, urllib.request, subprocess, tempfile
BASE = os.path.dirname(os.path.abspath(__file__))
cache = json.load(open(os.path.join(BASE, 'benchmark', 'topco_thumbs.json')))
out = os.path.join(BASE, 'docs', 'img', 'topco'); n = 0
for i, v in cache.items():
    dst = os.path.join(out, f'{i}.jpg')
    if not v.get('img') or os.path.exists(dst):
        continue
    try:
        b = urllib.request.urlopen(urllib.request.Request(v['img'], headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b); tmp = f.name
        subprocess.run(['sips', '-Z', '360', '-s', 'format', 'jpeg', '-s', 'formatOptions', '70', tmp, '--out', dst], capture_output=True)
        os.unlink(tmp); n += 1
    except Exception as e:
        print('fail', i, e)
    time.sleep(0.8)
print('saved', n, 'total', len(os.listdir(out)))

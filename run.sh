#!/bin/zsh
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:/usr/bin:/bin
log() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> tracker.log; }

# 실행 중에는 시스템 유휴 잠자기 방지
caffeinate -i -w $$ &

# 잠자기에서 막 깨어나면 네트워크가 없을 수 있음: 최대 30분까지 연결 대기
for i in {1..60}; do
  curl -sI -m 5 https://github.com >/dev/null 2>&1 && break
  [[ $i -eq 1 ]] && log "network not ready, waiting..."
  sleep 30
done
if ! curl -sI -m 5 https://github.com >/dev/null 2>&1; then
  log "ABORT: no network after 30 min"; exit 1
fi

python3 collect.py >> tracker.log 2>&1

# 수집이 전부 실패했으면(썸네일 캐시 제외) 빌드·커밋하지 않음
ok=$(sqlite3 tracker.db "select count(*) from runs where ts=(select max(ts) from runs) and ok=1 and source!='topco_thumbs';")
if [[ "$ok" -eq 0 ]]; then
  log "ABORT: all sources failed, skipping build/commit"; exit 1
fi

python3 thumbs.py >> tracker.log 2>&1
python3 build.py >> tracker.log 2>&1
git add docs benchmark data >> tracker.log 2>&1
git commit -qm "daily snapshot $(date +%Y-%m-%d)" >> tracker.log 2>&1

# 로컬에 앞선 커밋이 있으면 푸시(실패 시 3회 재시도)
if [[ -n "$(git log origin/main..main --oneline 2>/dev/null)" ]]; then
  for i in 1 2 3; do
    git push -q origin main >> tracker.log 2>&1 && break
    log "push failed (try $i)"; sleep 60
  done
fi

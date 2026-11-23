#!/bin/zsh
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:/usr/bin:/bin
python3 collect.py >> tracker.log 2>&1
python3 build.py >> tracker.log 2>&1
git add docs benchmark >> tracker.log 2>&1
git commit -qm "daily snapshot $(date +%Y-%m-%d)" >> tracker.log 2>&1 && git push -q origin main >> tracker.log 2>&1

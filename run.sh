#!/bin/zsh
cd "$(dirname "$0")"
/opt/homebrew/bin/python3 collect.py >> tracker.log 2>&1
/opt/homebrew/bin/python3 build.py >> tracker.log 2>&1

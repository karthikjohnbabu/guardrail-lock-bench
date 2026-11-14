#!/bin/bash
# Run every rung 5 times. Fast rungs first, the slow Qwen run last.
cd "$(dirname "$0")"
mkdir -p logs

for rung in B1 B3 B2 A1 A2 A4 A3; do
  echo "=== $rung started $(date '+%H:%M:%S') ==="
  python3 bench.py --rung "$rung" --runs 5 > "logs/$rung.log" 2>&1
  echo "=== $rung finished $(date '+%H:%M:%S') ==="
  tail -4 "logs/$rung.log"
done

echo "ALL DONE $(date '+%H:%M:%S')"

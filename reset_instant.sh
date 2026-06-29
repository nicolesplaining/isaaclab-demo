#!/usr/bin/env bash
# Kill all booth loops + training, then launch one booth_instant with given VIS.
VIS="${1:-128}"
for i in $(seq 1 15); do
  pkill -9 -f booth_instant.sh 2>/dev/null
  pkill -9 -f booth_g1.sh 2>/dev/null
  pkill -9 -f run_resume.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  sleep 1
done
sleep 3
echo "[reset_instant] launching booth_instant VIS=$VIS $(date)"
nohup bash ~/rl-demo/booth_instant.sh booth_seed model_100.pt 2048 "$VIS" >/tmp/boothinstant.out 2>&1 & disown

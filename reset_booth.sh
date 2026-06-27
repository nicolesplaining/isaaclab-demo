#!/usr/bin/env bash
# Kill ALL booth_g1 loops + training for 15s, then launch exactly one booth_g1.
for i in $(seq 1 15); do
  pkill -9 -f booth_g1.sh 2>/dev/null
  pkill -9 -f run_resume.sh 2>/dev/null
  pkill -9 -f run_train_viz.sh 2>/dev/null
  pkill -9 -f train_watchdog.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  sleep 1
done
sleep 3
echo "[reset] survivors booth_g1=$(pgrep -fc booth_g1.sh) kit=$(pgrep -fc _isaac_sim/kit/python) $(date)"
nohup bash ~/rl-demo/booth_g1.sh booth_seed model_100.pt 140 2048 16 >/tmp/boothg1.out 2>&1 & disown
echo "[reset] launched one booth_g1 $(date)"

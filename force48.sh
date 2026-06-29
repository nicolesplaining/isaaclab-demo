#!/usr/bin/env bash
# sustained-kill ALL launchers + training for 20s, then launch ONE booth_instant @48
for i in $(seq 1 20); do
  pkill -9 -f booth_instant.sh 2>/dev/null
  pkill -9 -f booth_g1.sh 2>/dev/null
  pkill -9 -f reset_instant.sh 2>/dev/null
  pkill -9 -f run_resume.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  sleep 1
done
sleep 3
echo "[force48] survivors: booth=$(pgrep -fc booth_instant.sh) kit=$(pgrep -fc _isaac_sim/kit/python)"
nohup bash ~/rl-demo/booth_instant.sh booth_seed model_110.pt 2048 48 >/tmp/boothinstant.out 2>&1 & disown
echo "[force48] launched ONE @48 $(date)"

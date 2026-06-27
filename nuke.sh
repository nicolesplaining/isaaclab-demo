#!/usr/bin/env bash
# Kill EVERYTHING demo-related for 30s straight (no launching). Reset to zero.
echo "[nuke] begin $(date)"
for i in $(seq 1 30); do
  pkill -9 -f booth_solo.sh 2>/dev/null
  pkill -9 -f booth_restart.sh 2>/dev/null
  pkill -9 -f booth_start.sh 2>/dev/null
  pkill -9 -f booth_loop.sh 2>/dev/null
  pkill -9 -f train_watchdog.sh 2>/dev/null
  pkill -9 -f run_train_viz.sh 2>/dev/null
  pkill -9 -f run_train.sh 2>/dev/null
  pkill -9 -f run_tensorboard.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  pkill -9 -f "python.sh scripts" 2>/dev/null
  pkill -9 -f dashboard_server.py 2>/dev/null
  pkill -9 -f "tensorboard.main" 2>/dev/null
  sleep 1
done
echo "[nuke] survivors:"
echo "  booth_scripts=$(pgrep -af 'booth_.*\.sh|run_train|run_tensorboard' | grep -v nuke.sh | grep -vc grep)"
echo "  kit_python=$(pgrep -fc '_isaac_sim/kit/python')"
echo "  dashboard=$(pgrep -fc dashboard_server.py)"
echo "  tensorboard=$(pgrep -fc tensorboard.main)"
echo "  ports 8080/8800/6006: $(ss -tln 2>/dev/null | grep -oE ':(8080|8800|6006)' | sort -u | tr '\n' ' ')"
echo "[nuke] done $(date)"

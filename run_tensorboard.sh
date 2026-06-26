#!/usr/bin/env bash
cd ~/rl-demo/IsaacLab
export TERM=xterm
pkill -9 -f "tensorboard.main" 2>/dev/null; sleep 1
exec ./isaaclab.sh -p -m tensorboard.main --logdir ~/rl-demo/IsaacLab/logs/rsl_rl --host 0.0.0.0 --port 6006 --reload_interval 5

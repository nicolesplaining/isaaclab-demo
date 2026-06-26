#!/usr/bin/env bash
set -e
cd ~/rl-demo
echo "[$(date)] Cloning IsaacSim..."
if [ ! -d IsaacSim ]; then
  git clone --depth=1 --recursive https://github.com/isaac-sim/IsaacSim
fi
cd IsaacSim
echo "[$(date)] git lfs install + pull..."
git lfs install
git lfs pull
echo "[$(date)] disk before build:"; df -h / | tail -1
echo "[$(date)] Building Isaac Sim (./build.sh)..."
./build.sh
echo "[$(date)] BUILD SCRIPT DONE. disk after:"; df -h / | tail -1
echo "ISAACSIM_BUILD_COMPLETE_MARKER"

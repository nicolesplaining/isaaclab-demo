#!/usr/bin/env bash
set -e
export ISAACSIM_PATH="$HOME/rl-demo/IsaacSim/_build/linux-aarch64/release"
export ISAACSIM_PYTHON_EXE="${ISAACSIM_PATH}/python.sh"
export LD_PRELOAD="$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1"
echo "[$(date)] ISAACSIM_PATH=$ISAACSIM_PATH"
ls -d "$ISAACSIM_PATH" >/dev/null || { echo "ISAACSIM_PATH missing"; exit 1; }
cd ~/rl-demo
if [ ! -d IsaacLab ]; then
  echo "[$(date)] Cloning IsaacLab..."
  git clone --recursive https://github.com/isaac-sim/IsaacLab
fi
cd IsaacLab
echo "[$(date)] symlink _isaac_sim -> $ISAACSIM_PATH"
ln -sfn "${ISAACSIM_PATH}" "${PWD}/_isaac_sim"
ls -l "${PWD}/_isaac_sim/python.sh"
echo "[$(date)] disk before install:"; df -h / | tail -1
echo "[$(date)] Running ./isaaclab.sh --install ..."
./isaaclab.sh --install
echo "[$(date)] ISAACLAB INSTALL DONE. disk:"; df -h / | tail -1
echo "ISAACLAB_INSTALL_COMPLETE_MARKER"

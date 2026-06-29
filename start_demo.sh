#!/usr/bin/env bash
# One command to bring up the booth demo and print where to open it.
# Prefers the systemd service (auto-starts on boot); falls back to a direct
# launch if the service is not installed.
set -u
SVC=booth-demo.service
cd ~/rl-demo

if systemctl --user cat "$SVC" >/dev/null 2>&1; then
  echo "[start_demo] ensuring systemd service is running: $SVC"
  systemctl --user start "$SVC"
else
  echo "[start_demo] service not installed; launching directly (nohup)"
  pkill -9 -f booth_instant.sh 2>/dev/null; sleep 2
  nohup bash ~/rl-demo/booth_instant.sh booth_seed model_110.pt 2048 48 \
    >~/rl-demo/booth_keepalive.log 2>&1 </dev/null & disown
fi

printf "[start_demo] waiting for Isaac Sim boot (~90s) "
for i in $(seq 1 45); do
  if ss -tln 2>/dev/null | grep -q ":8080\b" && grep -aq "Learning iteration" ~/rl-demo/train_viz.log 2>/dev/null; then
    ok=1; break
  fi
  printf "."; sleep 5
done
printf "\n"

LAN=$(hostname -I 2>/dev/null | awk "{print \$1}")
if [ "${ok:-0}" = "1" ]; then echo "[start_demo] booth is UP."; else echo "[start_demo] still booting; URLs below will work once the 3D view appears."; fi
cat <<URLS

  open in a browser:
    3D viewer (viser):  http://localhost:8080      LAN: http://$LAN:8080
    dashboard:          http://localhost:8800      LAN: http://$LAN:8800
    tensorboard:        http://localhost:6006      LAN: http://$LAN:6006

  manage:
    status:   systemctl --user status booth-demo
    logs:     journalctl --user -u booth-demo -f
    restart:  systemctl --user restart booth-demo
    stop:     systemctl --user stop booth-demo
URLS

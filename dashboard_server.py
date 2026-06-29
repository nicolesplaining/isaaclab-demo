#!/usr/bin/env python3
"""Booth dashboard for the DGX Spark live-RL demo.

Single client-facing page: embeds the live 3D viser view and renders clean
reward-up / episode-length-up / tracking-error-down charts parsed live from the
rsl_rl training log. No external/CDN dependencies (works offline at a booth).

Run:  python3 dashboard_server.py [--port 8000] [--log ~/rl-demo/train_viz.log]
Then open http://<spark-ip>:<port>/
"""
import argparse, json, os, re, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSI = re.compile(r"\x1b\[[0-9;]*m")
HOME = os.path.expanduser("~")
DEFAULT_LOG = os.path.join(HOME, "rl-demo", "train_viz.log")
START_EPOCH_FILE = os.path.join(HOME, "rl-demo", "train_start.epoch")
DONE_FLAG = "/tmp/trainviz.done"
CYCLE_TARGET = 140   # iterations per booth arc (display only)

FIELDS = {
    "iter":    re.compile(r"Learning iteration (\d+)/(\d+)"),
    "reward":  re.compile(r"Mean reward:\s*(-?[\d.]+)"),
    "ep_len":  re.compile(r"Mean episode length:\s*([\d.]+)"),
    "vel_err": re.compile(r"Metrics/base_velocity/error_vel_xy:\s*([\d.]+)"),
    "value_loss": re.compile(r"Mean value loss:\s*(-?[\d.]+)"),
    "success": re.compile(r"Metrics/success_rate:\s*([\d.]+)"),
    "sps":     re.compile(r"Steps per second:\s*([\d.]+)"),
    "ittime":  re.compile(r"Iteration time:\s*([\d.]+)s"),
}


def parse_log(path):
    try:
        with open(path, "r", errors="ignore") as f:
            text = ANSI.sub("", f.read())
        # instant-reset: only show metrics since the most recent reset marker
        _m = text.rfind("DEMO_RESET_MARKER")
        if _m != -1:
            text = text[_m:]
    except FileNotFoundError:
        return {"meta": {"status": "waiting", "current_iter": 0, "max_iter": 0,
                         "elapsed": 0, "sps": 0, "task": "", "envs": 0}, "series": []}

    iters = FIELDS["iter"].findall(text)
    def nums(key):
        return [float(x) for x in FIELDS[key].findall(text)]
    rewards, ep_lens = nums("reward"), nums("ep_len")
    vel_errs, vlosses = nums("vel_err"), nums("value_loss")
    succ, sps_all, ittimes = nums("success"), nums("sps"), nums("ittime")

    n = min(len(iters), len(rewards), len(ep_lens))
    series = []
    for i in range(n):
        series.append({
            "i": int(iters[i][0]),
            "reward": round(rewards[i], 3),
            "ep_len": round(ep_lens[i], 1),
            "vel_err": round(vel_errs[i], 4) if i < len(vel_errs) else None,
            "value_loss": round(vlosses[i], 4) if i < len(vlosses) else None,
            "success": round(succ[i], 3) if i < len(succ) else None,
        })

    # iterations counted within the current arc (since last reset / start)
    cur_iter = min(len(series), CYCLE_TARGET)
    max_iter = CYCLE_TARGET
    cur_sps = int(sps_all[-1]) if sps_all else 0

    # elapsed = smooth wall-clock since the run launched (start epoch written by
    # run_train_viz.sh). Falls back to summed iteration time if the file is missing.
    log_fresh0 = os.path.exists(path) and (time.time() - os.path.getmtime(path) < 20)
    elapsed = round(sum(ittimes), 1)
    try:
        with open(START_EPOCH_FILE) as f:
            ep = float(f.read().strip())
        live = time.time() - ep
        if log_fresh0:
            elapsed = round(max(0.0, live), 1)          # ticking while training
        else:
            elapsed = round(max(elapsed, 0.0), 1)        # frozen after run ends
    except Exception:
        pass

    # task / env count from the launcher header line
    task, envs = "", 0
    m = re.search(r"\] (\S+) iters=\d+ envs=(\d+)", text)
    if m:
        task, envs = m.group(1), int(m.group(2))

    # status
    log_fresh = os.path.exists(path) and (time.time() - os.path.getmtime(path) < 20)
    if not series:
        status = "warming up"
    elif cur_iter >= max_iter and max_iter > 0:
        status = "converged"
    elif os.path.exists(DONE_FLAG) and not log_fresh:
        status = "converged"
    elif log_fresh:
        status = "training"
    else:
        status = "idle"

    return {"meta": {"status": status, "current_iter": cur_iter, "max_iter": max_iter,
                     "elapsed": elapsed, "sps": cur_sps, "task": task, "envs": envs},
            "series": series}


class Handler(BaseHTTPRequestHandler):
    log_path = DEFAULT_LOG

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/metrics"):
            self._send(200, json.dumps(parse_log(self.log_path)))
        elif self.path.startswith("/api/restart"):
            # instant in-place reset: the training loop's hook reloads the seed
            # checkpoint + resets the robots on this flag (no simulator reboot).
            try:
                open("/tmp/demo_reset", "w").close()
            except Exception:
                pass
            self._send(200, json.dumps({"ok": True}))
        elif self.path == "/" or self.path.startswith("/index"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *a):
        pass


PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>DGX Spark — Live Reinforcement Learning</title>
<style>
  :root{ --bg:#08090b; --line:#181b20; --line2:#262a31; --txt:#edeff2; --dim:#767d87;
         --dim2:#474d56; --acc:#8ad94c; --cyan:#5ec9e8; }
  *{box-sizing:border-box; margin:0; padding:0}
  html,body{height:100%;background:var(--bg);color:var(--txt);
    font-family:-apple-system,'Inter','SF Pro Display',system-ui,'Segoe UI',sans-serif;
    overflow:hidden;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
  #app{height:100vh;display:flex;flex-direction:column}
  header{display:flex;align-items:center;justify-content:space-between;padding:22px 32px 18px}
  .brand{display:flex;align-items:center;gap:11px}
  .brand .dot{width:7px;height:7px;border-radius:50%;background:var(--acc)}
  .brand h1{font-size:15px;font-weight:600;letter-spacing:-.1px}
  .brand .sub{color:var(--dim);font-size:12px;margin-top:3px;font-weight:400;letter-spacing:.2px}
  .live{display:flex;align-items:center;gap:28px}
  .pill{display:flex;align-items:center;gap:8px;color:var(--acc);
    font-size:11px;font-weight:600;letter-spacing:1.6px;text-transform:uppercase}
  .pill .blink{width:6px;height:6px;border-radius:50%;background:var(--acc);animation:b 1.4s infinite}
  @keyframes b{0%,100%{opacity:1}50%{opacity:.28}}
  .clock{color:var(--dim);font-size:12px;text-align:right;line-height:1.55;letter-spacing:.2px}
  .clock b{color:var(--txt);font-weight:600}
  .restart{cursor:pointer;background:transparent;border:1px solid var(--line2);color:var(--txt);
    font-weight:500;font-size:12px;letter-spacing:.2px;padding:8px 15px;border-radius:8px;
    transition:border-color .15s,color .15s,transform .05s}
  .restart:hover{border-color:var(--acc);color:var(--acc)}
  .restart:active{transform:scale(.97)}
  .restart:disabled{opacity:.45;cursor:default}
  main{flex:1;display:grid;grid-template-columns:1.5fr 1fr;gap:20px;padding:0 32px 20px;min-height:0}
  .stage{position:relative;background:#000;border:1px solid var(--line);border-radius:16px;overflow:hidden}
  .stage iframe{width:100%;height:100%;border:0;display:block}
  .stage .tag{position:absolute;bottom:18px;left:20px;z-index:5;font-size:10.5px;letter-spacing:.8px;
    color:var(--dim);text-transform:uppercase;font-weight:500}
  .iterbox{position:absolute;top:20px;left:22px;z-index:5;display:flex;flex-direction:column;
    pointer-events:none;text-shadow:0 2px 18px rgba(0,0,0,.85)}
  .iterbox .k{font-size:11px;text-transform:uppercase;letter-spacing:3px;color:var(--dim);
    font-weight:600;margin-bottom:3px}
  .iterbox .v{display:flex;align-items:baseline;line-height:.9}
  .iterbox .v b{font-size:76px;font-weight:700;letter-spacing:-3px;color:var(--acc)}
  .iterbox .v .mx{font-size:26px;font-weight:500;color:var(--dim);letter-spacing:0;margin-left:4px}
  .stage .overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    flex-direction:column;gap:16px;background:#08090b;color:var(--dim);font-size:13px;z-index:20}
  .spin{width:30px;height:30px;border:2px solid var(--line2);border-top-color:var(--acc);
    border-radius:50%;animation:s .9s linear infinite}
  @keyframes s{to{transform:rotate(360deg)}}
  .right{display:grid;grid-template-rows:1fr 1fr 1fr;gap:18px;min-height:0}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);
    border:1px solid var(--line);border-radius:14px;overflow:hidden}
  .stat{background:var(--bg);padding:15px 18px}
  .stat .k{color:var(--dim);font-size:10px;text-transform:uppercase;letter-spacing:1.2px;font-weight:500}
  .stat .v{font-size:29px;font-weight:600;margin-top:7px;letter-spacing:-1px}
  .stat .v small{font-size:13px;color:var(--dim2);font-weight:500;letter-spacing:0}
  .card{display:flex;flex-direction:column;min-height:0}
  .card .h{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:3px}
  .card .h .t{font-size:10.5px;font-weight:500;color:var(--dim);text-transform:uppercase;letter-spacing:1px}
  .card .h .t .arrow{font-size:9.5px;margin-left:8px;color:var(--dim2);letter-spacing:.2px}
  .card .h .cur{font-size:21px;font-weight:600;letter-spacing:-.5px}
  .card canvas{flex:1;width:100%;min-height:0}
  footer{padding:14px 32px;border-top:1px solid var(--line);color:var(--dim2);font-size:11px;
    letter-spacing:.2px;display:flex;justify-content:space-between}
  .up{color:var(--acc)} .down{color:var(--cyan)}
  /* spotlight inset */
  .pip{position:absolute;right:16px;bottom:16px;width:31%;height:38%;border:1px solid var(--line2);
    border-radius:12px;overflow:hidden;background:#000;z-index:6;box-shadow:0 12px 34px rgba(0,0,0,.55)}
  .pip .plabel{position:absolute;top:11px;left:13px;z-index:7;display:flex;align-items:center;gap:6px;
    color:var(--dim);font-size:9.5px;font-weight:500;letter-spacing:.8px;text-transform:uppercase}
  .pip .plabel .d{width:5px;height:5px;border-radius:50%;background:var(--acc);animation:b 1.4s infinite}
  .pip iframe{position:absolute;top:50%;left:50%;width:270%;height:270%;
    transform:translate(-50%,-50%);border:0;pointer-events:none}
</style></head>
<body><div id="app">
  <header>
    <div class="brand">
      <div class="dot"></div>
      <div>
        <h1>Learning to walk</h1>
        <div class="sub" id="subtitle">Live reinforcement learning · NVIDIA DGX Spark</div>
      </div>
    </div>
    <div class="live">
      <div class="pill"><span class="blink"></span><span id="status">warming up</span></div>
      <div class="clock">
        <div><b id="sps">0</b> steps/s</div>
      </div>
      <button id="restartBtn" class="restart">⟳ Restart</button>
    </div>
  </header>

  <main>
    <div class="stage">
      <div class="iterbox">
        <span class="k">iteration</span>
        <span class="v"><b id="iter">0</b><span class="mx">/<span id="maxiter">140</span></span></span>
      </div>
      <iframe id="viser" referrerpolicy="no-referrer"></iframe>
      <div class="overlay" id="stageover"><div class="spin"></div>
        <div>Starting the simulation…</div></div>
      <div class="pip">
        <div class="plabel"><span class="d"></span>Spotlight view</div>
        <iframe id="viserpip" referrerpolicy="no-referrer"></iframe>
      </div>
    </div>

    <div class="right">
      <div class="card">
        <div class="h"><div class="t">Mean reward <span class="arrow up">▲ higher = better</span></div></div>
        <canvas id="ch_reward"></canvas>
      </div>
      <div class="card">
        <div class="h"><div class="t">Episode length <span class="arrow up">▲ stays standing longer</span></div></div>
        <canvas id="ch_eplen"></canvas>
      </div>
      <div class="card">
        <div class="h"><div class="t">Velocity tracking error <span class="arrow down">▼ lower = better</span></div></div>
        <canvas id="ch_velerr"></canvas>
      </div>
    </div>
  </main>
</div>

<script>
const host = location.hostname || "localhost";
const viser = document.getElementById("viser");
let viserUp = false;
const viserpip = document.getElementById("viserpip");
function tryViser(){
  // main view (static crowd) + spotlight inset (tracks the hero); both point at viser
  viser.src = "http://"+host+":8080/";
  viserpip.src = "http://"+host+":8080/";
}
tryViser();

function fmt(n,d=2){ if(n===null||n===undefined||isNaN(n)) return "–"; return Number(n).toFixed(d); }
function fmtTime(s){ s=Math.round(s); const m=Math.floor(s/60); return m? m+"m "+(s%60)+"s" : s+"s"; }

// --- minimal canvas line chart (no deps) ---
function drawChart(cv, vals, opts){
  const dpr = window.devicePixelRatio||1;
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w*dpr; cv.height = h*dpr;
  const x = cv.getContext("2d"); x.scale(dpr,dpr);
  x.clearRect(0,0,w,h);
  const pad = {l:38,r:8,t:8,b:16};
  const iw = w-pad.l-pad.r, ih = h-pad.t-pad.b;
  if(!vals.length){ return; }
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if(opts.lo!==undefined) lo=Math.min(lo,opts.lo);
  if(opts.hi!==undefined) hi=Math.max(hi,opts.hi);
  if(hi-lo < 1e-6){ hi=lo+1; }
  const padv=(hi-lo)*0.12; lo-=padv; hi+=padv;
  const X = i => pad.l + (vals.length===1?iw/2:iw*i/(vals.length-1));
  const Y = v => pad.t + ih*(1-(v-lo)/(hi-lo));
  // faint gridlines + y labels
  x.strokeStyle="#15181d"; x.fillStyle="#474d56"; x.font="10px -apple-system,Inter,sans-serif"; x.lineWidth=1;
  for(let g=0; g<=2; g++){
    const yy = pad.t + ih*g/2; const val = hi-(hi-lo)*g/2;
    x.beginPath(); x.moveTo(pad.l,yy); x.lineTo(w-pad.r,yy); x.stroke();
    x.fillText(val.toFixed(opts.dec||0), 4, yy+3);
  }
  // zero line
  if(lo<0 && hi>0){ const z=Y(0); x.strokeStyle="#262a31"; x.setLineDash([3,4]);
    x.beginPath(); x.moveTo(pad.l,z); x.lineTo(w-pad.r,z); x.stroke(); x.setLineDash([]); }
  // subtle area fill
  const grad = x.createLinearGradient(0,pad.t,0,pad.t+ih);
  grad.addColorStop(0, opts.fill); grad.addColorStop(1, "rgba(0,0,0,0)");
  x.beginPath(); x.moveTo(X(0),Y(vals[0]));
  for(let i=1;i<vals.length;i++) x.lineTo(X(i),Y(vals[i]));
  x.lineTo(X(vals.length-1), pad.t+ih); x.lineTo(X(0), pad.t+ih); x.closePath();
  x.fillStyle=grad; x.fill();
  // line
  x.beginPath(); x.moveTo(X(0),Y(vals[0]));
  for(let i=1;i<vals.length;i++) x.lineTo(X(i),Y(vals[i]));
  x.strokeStyle=opts.color; x.lineWidth=1.8; x.lineJoin="round"; x.stroke();
  // head dot
  const lx=X(vals.length-1), ly=Y(vals[vals.length-1]);
  x.beginPath(); x.arc(lx,ly,2.6,0,7); x.fillStyle=opts.color; x.fill();
}

async function tick(){
  let d;
  try{ d = await (await fetch("/api/metrics",{cache:"no-store"})).json(); }
  catch(e){ return; }
  const m=d.meta, s=d.series;
  document.getElementById("status").textContent =
     m.status==="training"?"training live": m.status;
  document.getElementById("iter").textContent = m.current_iter;
  document.getElementById("maxiter").textContent = m.max_iter;
  document.getElementById("sps").textContent = (m.sps||0).toLocaleString();

  // viser overlay: hide once we have iterations (sim is running)
  const over=document.getElementById("stageover");
  over.style.display = (s.length>0) ? "none" : "flex";

  if(!s.length){ requestAnimationFrame(()=>{}); return; }
  const reward=s.map(p=>p.reward), eplen=s.map(p=>p.ep_len),
        velerr=s.map(p=>p.vel_err).filter(v=>v!==null);
  const last=s[s.length-1];
  // draw
  drawChart(document.getElementById("ch_reward"), reward,
     {color:"#8ad94c", fill:"rgba(138,217,76,.12)", dec:0});
  drawChart(document.getElementById("ch_eplen"), eplen,
     {color:"#8ad94c", fill:"rgba(138,217,76,.10)", lo:0, hi:1000, dec:0});
  drawChart(document.getElementById("ch_velerr"), velerr,
     {color:"#5ec9e8", fill:"rgba(94,201,232,.10)", lo:0, dec:2});
}
// restart button: tells the server to kill the current run; the booth loop then
// starts a fresh cycle from the checkpoint (~90s to reboot the simulator).
const rbtn = document.getElementById("restartBtn");
rbtn.addEventListener("click", async () => {
  rbtn.disabled = true; const orig = rbtn.textContent; rbtn.textContent = "⟳ Reset!";
  try { await fetch("/api/restart"); } catch(e){}
  setTimeout(() => { rbtn.disabled = false; rbtn.textContent = orig; }, 2500);
});
setInterval(tick, 1500); tick();
window.addEventListener("resize", tick);
</script>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--log", default=DEFAULT_LOG)
    args = ap.parse_args()
    Handler.log_path = os.path.expanduser(args.log)
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"[dashboard] http://0.0.0.0:{args.port}/  (log={Handler.log_path})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()

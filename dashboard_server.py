#!/usr/bin/env python3
"""Booth dashboard for the DGX Spark live-RL demo.

Single client-facing page: embeds the live 3D viser view and renders clean
reward-up / episode-length-up / tracking-error-down charts parsed live from the
rsl_rl training log. No external/CDN dependencies (works offline at a booth).

Run:  python3 dashboard_server.py [--port 8000] [--log ~/rl-demo/train_viz.log]
Then open http://<spark-ip>:<port>/
"""
import argparse, json, os, re, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSI = re.compile(r"\x1b\[[0-9;]*m")
HOME = os.path.expanduser("~")
DEFAULT_LOG = os.path.join(HOME, "rl-demo", "train_viz.log")
START_EPOCH_FILE = os.path.join(HOME, "rl-demo", "train_start.epoch")
DONE_FLAG = "/tmp/trainviz.done"

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

    max_iter = int(iters[-1][1]) if iters else 0
    cur_iter = int(iters[-1][0]) if iters else 0
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
  :root{ --bg:#0a0e0a; --panel:#11171a; --line:#1f2a2a; --green:#76b900; --green2:#a4e400;
         --cyan:#00d0ff; --amber:#ffb000; --txt:#e8f0e8; --dim:#7f8c87; }
  *{box-sizing:border-box; margin:0; padding:0}
  html,body{height:100%;background:var(--bg);color:var(--txt);
    font-family:'Segoe UI',Helvetica,Arial,sans-serif;overflow:hidden}
  #app{height:100vh;display:flex;flex-direction:column}
  header{display:flex;align-items:center;justify-content:space-between;
    padding:14px 26px;border-bottom:1px solid var(--line);
    background:linear-gradient(90deg,#0d120d, #0a0e0a)}
  .brand{display:flex;align-items:center;gap:14px}
  .brand .dot{width:12px;height:12px;border-radius:50%;background:var(--green);
    box-shadow:0 0 14px var(--green)}
  .brand h1{font-size:20px;font-weight:600;letter-spacing:.3px}
  .brand .sub{color:var(--dim);font-size:13px;margin-top:2px}
  .live{display:flex;align-items:center;gap:18px}
  .pill{display:flex;align-items:center;gap:8px;background:#1a2410;border:1px solid #2f3f18;
    color:var(--green2);padding:7px 14px;border-radius:999px;font-weight:700;font-size:13px;
    letter-spacing:1px;text-transform:uppercase}
  .pill .blink{width:9px;height:9px;border-radius:50%;background:var(--green2);
    animation:b 1.1s infinite}
  @keyframes b{0%,100%{opacity:1}50%{opacity:.25}}
  .clock{color:var(--dim);font-size:13px;text-align:right}
  .clock b{color:var(--txt);font-size:15px}
  main{flex:1;display:grid;grid-template-columns:1.35fr 1fr;gap:14px;padding:14px;min-height:0}
  .stage{position:relative;background:#000;border:1px solid var(--line);border-radius:12px;
    overflow:hidden}
  .stage iframe{width:100%;height:100%;border:0;display:block}
  .stage .tag{position:absolute;top:12px;left:14px;z-index:5;background:rgba(0,0,0,.55);
    backdrop-filter:blur(4px);padding:6px 12px;border-radius:8px;font-size:13px;color:#cfe8b0;
    border:1px solid #2a3a18}
  .stage .overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    flex-direction:column;gap:14px;background:radial-gradient(circle at 50% 40%,#0c140c,#000);
    color:var(--dim);font-size:15px;z-index:4}
  .spin{width:38px;height:38px;border:3px solid #243018;border-top-color:var(--green);
    border-radius:50%;animation:s 1s linear infinite}
  @keyframes s{to{transform:rotate(360deg)}}
  .right{display:grid;grid-template-rows:auto 1fr 1fr 1fr;gap:12px;min-height:0}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
  .stat .k{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:1px}
  .stat .v{font-size:26px;font-weight:700;margin-top:3px}
  .stat .v small{font-size:13px;color:var(--dim);font-weight:500}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:10px 12px;display:flex;flex-direction:column;min-height:0}
  .card .h{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:4px}
  .card .h .t{font-size:13px;font-weight:600}
  .card .h .t .arrow{font-size:12px;margin-left:6px}
  .card .h .cur{font-size:20px;font-weight:700}
  .card canvas{flex:1;width:100%;min-height:0}
  footer{padding:8px 26px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;
    display:flex;justify-content:space-between}
  .up{color:var(--green2)} .down{color:var(--cyan)}
  /* picture-in-picture spotlight: zoomed view of the centre robot(s) */
  .pip{position:absolute;right:14px;bottom:14px;width:30%;height:36%;border:2px solid var(--green);
    border-radius:10px;overflow:hidden;background:#000;z-index:6;
    box-shadow:0 0 24px rgba(118,185,0,.45),0 8px 22px rgba(0,0,0,.65)}
  .pip .plabel{position:absolute;top:0;left:0;right:0;z-index:7;padding:6px 9px;display:flex;
    align-items:center;gap:7px;color:var(--green2);font-size:12px;font-weight:700;letter-spacing:.4px;
    background:linear-gradient(180deg,rgba(0,0,0,.8),rgba(0,0,0,0))}
  .pip .plabel .d{width:8px;height:8px;border-radius:50%;background:var(--green2);
    box-shadow:0 0 9px var(--green2);animation:b 1.1s infinite}
  .pip iframe{position:absolute;top:50%;left:50%;width:270%;height:270%;
    transform:translate(-50%,-50%);border:0;pointer-events:none}
</style></head>
<body><div id="app">
  <header>
    <div class="brand">
      <div class="dot"></div>
      <div>
        <h1>A robot learns to walk — live on NVIDIA DGX Spark</h1>
        <div class="sub" id="subtitle">Reinforcement learning from scratch · on-device · GB10 Blackwell</div>
      </div>
    </div>
    <div class="live">
      <div class="pill"><span class="blink"></span><span id="status">warming up</span></div>
      <div class="clock">
        <div>iteration <b id="iter">0</b> / <span id="maxiter">0</span></div>
        <div>elapsed <b id="elapsed">0s</b> · <span id="sps">0</span> steps/s</div>
      </div>
    </div>
  </header>

  <main>
    <div class="stage">
      <div class="tag" id="stagetag">live physics · one robot learning to walk</div>
      <iframe id="viser" referrerpolicy="no-referrer"></iframe>
      <div class="overlay" id="stageover"><div class="spin"></div>
        <div>Starting the simulation…</div></div>
      <div class="pip">
        <div class="plabel"><span class="d"></span>SPOTLIGHT · tracking one robot</div>
        <iframe id="viserpip" referrerpolicy="no-referrer"></iframe>
      </div>
    </div>

    <div class="right">
      <div class="stats">
        <div class="stat"><div class="k">Reward</div><div class="v" id="s_reward">–</div></div>
        <div class="stat"><div class="k">Stays upright</div><div class="v" id="s_eplen">–<small>/1000</small></div></div>
        <div class="stat"><div class="k">Tracking error</div><div class="v" id="s_velerr">–</div></div>
      </div>
      <div class="card">
        <div class="h"><div class="t">Mean reward <span class="arrow up">▲ higher = better</span></div>
          <div class="cur up" id="c_reward">–</div></div>
        <canvas id="ch_reward"></canvas>
      </div>
      <div class="card">
        <div class="h"><div class="t">Episode length <span class="arrow up">▲ stays standing longer</span></div>
          <div class="cur up" id="c_eplen">–</div></div>
        <canvas id="ch_eplen"></canvas>
      </div>
      <div class="card">
        <div class="h"><div class="t">Velocity tracking error <span class="arrow down">▼ lower = better</span></div>
          <div class="cur down" id="c_velerr">–</div></div>
        <canvas id="ch_velerr"></canvas>
      </div>
    </div>
  </main>

  <footer>
    <div id="task">Isaac Lab · rsl_rl PPO · Unitree Go2 velocity tracking</div>
    <div>NVIDIA DGX Spark · Isaac Sim 6.0 + Isaac Lab · GPU PhysX</div>
  </footer>
</div>

<script>
const host = location.hostname || "localhost";
const viser = document.getElementById("viser");
let viserUp = false;
const viserpip = document.getElementById("viserpip");
function tryViser(){
  // viser serves on :8080; main view + zoomed spotlight both point at it.
  // The follow-camera keeps the tracked robot centered, so the centre-zoomed
  // spotlight automatically stays locked on it.
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
  // gridlines + y labels
  x.strokeStyle="#1b2420"; x.fillStyle="#5f6b63"; x.font="10px Segoe UI"; x.lineWidth=1;
  for(let g=0; g<=3; g++){
    const yy = pad.t + ih*g/3; const val = hi-(hi-lo)*g/3;
    x.beginPath(); x.moveTo(pad.l,yy); x.lineTo(w-pad.r,yy); x.stroke();
    x.fillText(val.toFixed(opts.dec||0), 4, yy+3);
  }
  // zero line
  if(lo<0 && hi>0){ const z=Y(0); x.strokeStyle="#33403a"; x.setLineDash([4,4]);
    x.beginPath(); x.moveTo(pad.l,z); x.lineTo(w-pad.r,z); x.stroke(); x.setLineDash([]); }
  // area fill
  const grad = x.createLinearGradient(0,pad.t,0,pad.t+ih);
  grad.addColorStop(0, opts.fill); grad.addColorStop(1, "rgba(0,0,0,0)");
  x.beginPath(); x.moveTo(X(0),Y(vals[0]));
  for(let i=1;i<vals.length;i++) x.lineTo(X(i),Y(vals[i]));
  x.lineTo(X(vals.length-1), pad.t+ih); x.lineTo(X(0), pad.t+ih); x.closePath();
  x.fillStyle=grad; x.fill();
  // line
  x.beginPath(); x.moveTo(X(0),Y(vals[0]));
  for(let i=1;i<vals.length;i++) x.lineTo(X(i),Y(vals[i]));
  x.strokeStyle=opts.color; x.lineWidth=2.4; x.lineJoin="round"; x.stroke();
  // head dot
  const lx=X(vals.length-1), ly=Y(vals[vals.length-1]);
  x.beginPath(); x.arc(lx,ly,3.5,0,7); x.fillStyle=opts.color; x.fill();
  x.beginPath(); x.arc(lx,ly,7,0,7); x.strokeStyle=opts.color; x.globalAlpha=.3; x.stroke(); x.globalAlpha=1;
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
  document.getElementById("elapsed").textContent = fmtTime(m.elapsed);
  document.getElementById("sps").textContent = (m.sps||0).toLocaleString();
  if(m.envs){ document.getElementById("stagetag").textContent =
     "live physics · learning from "+m.envs.toLocaleString()+" robots in parallel"; }
  if(m.task){ document.getElementById("task").textContent =
     "Isaac Lab · rsl_rl PPO · "+m.task; }

  // viser overlay: hide once we have iterations (sim is running)
  const over=document.getElementById("stageover");
  over.style.display = (s.length>0) ? "none" : "flex";

  if(!s.length){ requestAnimationFrame(()=>{}); return; }
  const reward=s.map(p=>p.reward), eplen=s.map(p=>p.ep_len),
        velerr=s.map(p=>p.vel_err).filter(v=>v!==null);
  const last=s[s.length-1];
  // stat tiles
  document.getElementById("s_reward").textContent = fmt(last.reward,1);
  document.getElementById("s_eplen").innerHTML = Math.round(last.ep_len)+'<small>/1000</small>';
  document.getElementById("s_velerr").textContent = fmt(last.vel_err,2);
  // chart current labels
  document.getElementById("c_reward").textContent = fmt(last.reward,2);
  document.getElementById("c_eplen").textContent = Math.round(last.ep_len);
  document.getElementById("c_velerr").textContent = fmt(last.vel_err,3);
  // draw
  drawChart(document.getElementById("ch_reward"), reward,
     {color:"#a4e400", fill:"rgba(118,185,0,.28)", dec:0});
  drawChart(document.getElementById("ch_eplen"), eplen,
     {color:"#76b900", fill:"rgba(118,185,0,.22)", lo:0, hi:1000, dec:0});
  drawChart(document.getElementById("ch_velerr"), velerr,
     {color:"#00d0ff", fill:"rgba(0,208,255,.20)", lo:0, dec:2});
}
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

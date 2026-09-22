"""
Local round trip for the SWMM corpus, in three phases:

  encode  decode every unique corpus .inp with swmm-utils and write the
          re-encoded file next to a copy of the original (host, fast)
  run     ONE container runs the real SWMM 5.2.4 engine on every original
          and re-encoded file, N at a time, each capped at RT_TIMEOUT s
          (the engine reports input errors before routing starts, so a
          timeout still tells us whether the file parsed)
  report  compare: a file whose original parses but whose re-encoding
          throws an engine ERROR is an encoder/decoder bug; a per-section
          token audit flags dropped columns/rows the engine tolerated

Usage: python scripts/swmm_engine_roundtrip.py encode|run|report|all [substring-filter]

Needs docker (the SWMM task image, pulled from ECR) and the swmm-utils
checkout you want to test installed in the current environment. Found six
encoder/decoder bugs the first time it ran (September 2026): AQUIFERS,
BUILDUP and HYDROGRAPHS columns, and EVENTS / GWF / LOADINGS dropped.
"""
import hashlib, json, os, subprocess, sys, time
from collections import Counter
from pathlib import Path

CORPUS = Path(os.environ.get("SWMM_CORPUS", Path(__file__).resolve().parent.parent / "EPASWMM Example Files"))
HERE = Path(__file__).parent
STATE = Path(__file__).with_name("swmm_engine_roundtrip_state.json")
WORK = Path(os.environ.get("RT_WORK", Path(__file__).with_name("swmm_engine_roundtrip_work")))
IMG = os.environ.get("SWMM_TASK_IMAGE", "087383746182.dkr.ecr.us-east-2.amazonaws.com/wrm/swmm-task:5.2.4-swmm-utils-1.2.1")
SKIP = {"TITLE", "TAGS", "MAP", "PROFILES", "REPORT", "OPTIONS", "FILES", "BACKDROP", "LABELS", "SYMBOLS"}
EXTRA_EXT = (".dat", ".txt", ".hsf", ".rff", ".csv", ".hot", ".rain", ".prc", ".tmp", ".clim")

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def load(): return json.loads(STATE.read_text()) if STATE.exists() else {}
def save(st): STATE.write_text(json.dumps(st, indent=1))

def unique_files():
    seen = {}
    for p in sorted(CORPUS.rglob("*.inp")):
        d = hashlib.md5(p.read_bytes()).hexdigest(); rel = str(p.relative_to(CORPUS))
        if d not in seen or len(rel) < len(seen[d]): seen[d] = rel
    return sorted(seen.values())

def workdir(rel): return WORK / hashlib.md5(rel.encode()).hexdigest()[:10]

def sections(text):
    out, cur = {}, None
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("["):
            cur = s.strip("[]").upper(); out.setdefault(cur, []); continue
        if cur is None or not s or s.startswith(";"): continue
        out[cur].append(s.split(";")[0].split())
    return out

def audit(orig, enc):
    a, b = sections(orig), sections(enc); diff = {}
    for sec in sorted(set(a) | set(b)):
        if sec in SKIP: continue
        ra, rb = a.get(sec, []), b.get(sec, [])
        ta = max((len(r) for r in ra), default=0); tb = max((len(r) for r in rb), default=0)
        if len(ra) != len(rb) or ta != tb:
            diff[sec] = {"rows": [len(ra), len(rb)], "max_tokens": [ta, tb]}
    return diff

def do_encode(state, flt):
    from swmm_utils import SwmmInput
    WORK.mkdir(exist_ok=True)
    files = [r for r in unique_files() if (flt is None or flt in r)]
    log("encoding", len(files))
    for rel in files:
        src = CORPUS / rel; d = workdir(rel); d.mkdir(exist_ok=True)
        e = state.setdefault(rel, {}); e["dir"] = d.name
        orig = src.read_text(errors="replace"); (d / "orig.inp").write_text(orig)
        for sib in src.parent.iterdir():
            if sib.is_file() and sib.suffix.lower() in EXTRA_EXT and not (d / sib.name).exists():
                try: (d / sib.name).write_bytes(sib.read_bytes())
                except OSError: pass
        try:
            t0 = time.time(); SwmmInput(src).to_inp(d / "enc.inp"); e["encode_seconds"] = round(time.time() - t0, 1)
            e.pop("encode_error", None)
            e["audit"] = audit(orig, (d / "enc.inp").read_text(errors="replace"))
        except Exception as ex:  # noqa: BLE001
            e["encode_error"] = f"{type(ex).__name__}: {ex}"[:200]
    save(state)
    log("encoded; encode errors:", sum(1 for e in state.values() if e.get("encode_error")))

def do_run(state, flt):
    jobs = WORK / "jobs.txt"
    lines = []
    for rel, e in state.items():
        if flt and flt not in rel: continue
        for name in ("orig", "enc"):
            if (workdir(rel) / f"{name}.inp").exists() and not (workdir(rel) / f"{name}.rpt").exists():
                lines.append(f"{e['dir']} {name}")
    jobs.write_text("\n".join(lines) + "\n")
    log("running", len(lines), "engine jobs in one container")
    par = os.environ.get("RT_PAR", "6"); to = os.environ.get("RT_TIMEOUT", "180")
    script = (
        "cd /w && cat jobs.txt | xargs -P %s -L 1 sh -c "
        "'cd /w/$0 && timeout %s /app/bin/runswmm $1.inp $1.rpt $1.out >/dev/null 2>&1; rc=$?; "
        "[ -f $1.rpt ] || echo \"TIMEOUT-OR-CRASH rc=$rc\" > $1.rpt; rm -f $1.out; echo \"$0 $1 rc=$rc\"'" % (par, to))
    t0 = time.time()
    p = subprocess.run(["docker", "run", "--rm", "--entrypoint", "sh", "-v", f"{WORK}:/w", IMG, "-c", script],
                       capture_output=True, text=True)
    (WORK / "run.log").write_text(p.stdout + p.stderr)
    log(f"engine done in {time.time() - t0:.0f}s; lines {len(p.stdout.splitlines())}")

def read_rpt(path):
    if not path.exists(): return {"error": "no rpt", "detail": ""}
    lines = path.read_text(errors="replace").splitlines()
    for i, ln in enumerate(lines):
        if "ERROR" in ln:
            return {"error": ln.strip()[:160], "detail": (lines[i + 1].strip()[:120] if i + 1 < len(lines) else "")}
    return {"error": "", "detail": ""}

def do_report(state):
    for rel, e in state.items():
        if "dir" not in e: continue
        for name in ("orig", "enc"):
            e[name] = read_rpt(workdir(rel) / f"{name}.rpt")
    save(state)
    regress = {r: e for r, e in state.items() if e.get("orig", {}).get("error") == "" and e.get("enc", {}).get("error")}
    print(f"\nfiles {len(state)} | encode errors {sum(1 for e in state.values() if e.get('encode_error'))} | "
          f"original errors {sum(1 for e in state.values() if e.get('orig', {}).get('error'))} | "
          f"re-encoded errors where original ran {len(regress)} | files with audit diffs {sum(1 for e in state.values() if e.get('audit'))}")
    print("\nregressions by engine message + section:")
    for (msg, sec), n in Counter((e["enc"]["error"].split(" at line")[0], e["enc"]["error"].split("of ")[-1].rstrip(":") if " of " in e["enc"]["error"] else "") for e in regress.values()).most_common(30):
        print(f"  {n:4}  {msg:55} {sec}")
    print("\naudit diffs by section (files, and the commonest rows/max_tokens change):")
    per = {}
    for e in state.values():
        for sec, d in (e.get("audit") or {}).items():
            per.setdefault(sec, Counter())[f"rows {d['rows'][0]}->{d['rows'][1]} tokens {d['max_tokens'][0]}->{d['max_tokens'][1]}"] += 1
    for sec, c in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {sum(c.values()):4}  {sec:16} e.g. {c.most_common(1)[0][0]}")
    print("\nencode errors:")
    for msg, n in Counter(e["encode_error"] for e in state.values() if e.get("encode_error")).most_common(10):
        print(f"  {n:4}  {msg}")

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    flt = sys.argv[2] if len(sys.argv) > 2 else None
    state = load()
    if stage in ("encode", "all"): do_encode(state, flt)
    if stage in ("run", "all"): do_run(state, flt)
    if stage in ("report", "all"): do_report(state)

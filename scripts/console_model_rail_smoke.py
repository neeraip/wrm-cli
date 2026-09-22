"""
Console hydraulic-model rail smoke test.

Ten SWMM models from this repo's corpus, pushed through the NEER Console
model rail the way a user would: import the .inp, wait for the parse, read
the model's data.json, change the report step and one conduit's cross
section through the data API, read them back, run the simulation through
Console (which renders source.inp + overlay and forwards to the WRM API),
wait for it, then check the artifacts the producer post-step should have
written and that both edits reached the .rpt and the rendered input.

Run it before releasing swmm-utils, lambda-importer or the SWMM task image.
It found three platform bugs the first time it ran (September 2026):
storage nodes dropped at import, [LANDUSES] rendered with too few columns,
and cross-section edits discarded at render.

    export NEER_API_KEY=nck_...            # Console API key (User settings → API keys)
    export PROJECT_ID=<console project id> # a project in a team that holds a WRM API key
    export CONSOLE_BASE=https://aip-dev.neer.ai   # default
    python scripts/console_model_rail_smoke.py all [--only <substring>]

Stages: import | edit | run | check | all. State is kept beside this script
in console_model_rail_smoke_state.json so a stage can be re-run; delete it
(or an entry's layer_id/model_id) to import a file afresh.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = os.environ.get("CONSOLE_BASE", "https://aip-dev.neer.ai")
KEY = os.environ["NEER_API_KEY"]
PROJECT = os.environ["PROJECT_ID"]
CORPUS = Path(__file__).resolve().parent.parent / "EPASWMM Example Files"
STATE = Path(__file__).with_name("console_model_rail_smoke_state.json")

# Chosen for variety: LID, hydrology with 3,972 subcatchments, 46 pumps,
# weirs, orifices with PID control, water quality, two semi-real networks
# including a 19 MB one with 4,569 nodes, and an OWA custom-shape case.
FILES = [
    "EPA/Example_LID_RB.inp",
    "Hydrology/3974_Subs_Horton.inp",
    "Pumps/46_pumps.inp",
    "Weirs/extran4_roadway.inp",
    "Orifices/extran3_bottom_orifice_pid.inp",
    "WQ/PeterKlaver_WQ_Tracer.inp",
    "LID/turf_lid_model.inp",
    "Semi_Real_Models/79_Pumps_440_H&H_Elements.inp",
    "Semi_Real_Models/4569_Nodes.inp",
    "OWA_EXTRAN/barrels_custom_shape.inp",
]

S = requests.Session()
S.headers["Authorization"] = f"Bearer {KEY}"
# A status poll that times out while the cluster is busy must not end the run.
from requests.adapters import HTTPAdapter  # noqa: E402
from urllib3.util.retry import Retry  # noqa: E402
S.mount("https://", HTTPAdapter(max_retries=Retry(total=6, backoff_factor=2, status_forcelist=[502, 503, 504])))


def wanted(rel, only):
    """`only` is None (everything), a substring, or a set of files."""
    if only is None:
        return True
    if isinstance(only, str):
        return only in rel
    return rel in only


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(state):
    STATE.write_text(json.dumps(state, indent=2, default=str))


def name_of(rel):
    return rel.replace("/", " · ").removesuffix(".inp")


# ---------------------------------------------------------------- import
def do_import(state, only):
    for rel in (sorted(only) if isinstance(only, (set, list, tuple)) else FILES):
        if not wanted(rel, only):
            continue
        entry = state.setdefault(rel, {})
        if entry.get("layer_id"):
            continue
        path = CORPUS / rel
        with open(path, "rb") as fh:
            r = S.post(
                f"{BASE}/api/v1/projects/{PROJECT}/models/from-inp",
                files={"file": (path.name, fh, "text/plain")},
                data={"model_name": name_of(rel)},
                timeout=600,
            )
        entry["import_http"] = r.status_code
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:300]}
        entry["import_response"] = body
        entry["layer_id"] = body.get("layer_id")
        log("import", rel, r.status_code, body.get("layer_id") or body)
        save(state)


def wait_import(state, only, timeout=900):
    pending = {rel for rel, e in state.items() if e.get("layer_id") and not e.get("model_id") and wanted(rel, only)}
    t0 = time.time()
    while pending and time.time() - t0 < timeout:
        for rel in sorted(pending):
            e = state[rel]
            r = S.get(f"{BASE}/api/v1/layers/{e['layer_id']}/hydraulic-model", timeout=60)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:200]}
            status = body.get("status")
            if status == "done":
                e["model_id"] = body["model_id"]
                e["import_status"] = "done"
                e["import_seconds"] = round(time.time() - t0)
                log("parsed", rel, "model", e["model_id"])
                pending.discard(rel)
            elif status == "failed":
                e["import_status"] = "failed"
                e["import_error"] = body.get("error")
                log("PARSE FAILED", rel, body.get("error"))
                pending.discard(rel)
        save(state)
        if pending:
            time.sleep(10)
    for rel in pending:
        state[rel]["import_status"] = "timeout"
        log("import timeout", rel)
    save(state)


# ---------------------------------------------------------------- edit
def pick_edits(data):
    """
    Two changes that must survive the overlay: the report step (always to
    a value it is not at now) and, where the model has one, the first
    conduit's full depth scaled by 1.5 — a real change to the network.
    Returns [(path, before, after, kind)].
    """
    edits = []
    options = data.get("options") or {}
    key = next((k for k in options if k.lower().replace("_", "") == "reportstep"), "REPORT_STEP")
    before = options.get(key)
    after = "00:10:00" if str(before).strip() == "00:15:00" else "00:15:00"
    edits.append((f"options/{key}", before, after, "report_step"))
    xs = data.get("xsections")
    if isinstance(xs, list) and xs:
        row = xs[0]
        try:
            g1 = float(row.get("geom1"))
        except (TypeError, ValueError):
            g1 = None
        if g1 and g1 > 0:
            edits.append((f"xsections/0/geom1", row.get("geom1"), f"{g1 * 1.5:g}", f"geom1:{row.get('link')}"))
    return edits


def _get_path(data, path):
    cur = data
    for seg in path.split("/"):
        if isinstance(cur, list):
            cur = cur[int(seg)]
        elif isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            return None
    return cur


def do_edit(state, only):
    for rel, e in state.items():
        if not wanted(rel, only):
            continue
        if not e.get("model_id") or e.get("edit_status") == "ok":
            continue
        mid = e["model_id"]
        r = S.get(f"{BASE}/api/v1/models/{mid}/data", timeout=120)
        if r.status_code != 200:
            e["edit_status"] = f"read {r.status_code}: {r.text[:200]}"
            log("data read failed", rel, e["edit_status"])
            continue
        snap = r.json()
        data = snap.get("data") or {}
        e["data_sections"] = sorted(data.keys()) if isinstance(data, dict) else str(type(data))
        e["etag_before"] = snap.get("etag")
        edits = pick_edits(data)
        e["edits"] = [{"path": p, "before": b, "after": a, "kind": k} for p, b, a, k in edits]
        r = S.patch(
            f"{BASE}/api/v1/models/{mid}/data",
            json={"ops": [{"op": "set", "path": p, "value": a} for p, _, a, _ in edits], "etag": snap.get("etag")},
            timeout=120,
        )
        e["patch_http"] = r.status_code
        if r.status_code != 200:
            e["edit_status"] = f"patch {r.status_code}: {r.text[:300]}"
            log("PATCH FAILED", rel, e["edit_status"])
            save(state)
            continue
        e["etag_after"] = r.json().get("etag")
        # Read back: the reparse of the overlay must show the new values.
        data2 = S.get(f"{BASE}/api/v1/models/{mid}/data", timeout=120).json().get("data") or {}
        mismatches = []
        for p, _, a, _ in edits:
            got = _get_path(data2, p)
            if str(got) != str(a):
                mismatches.append(f"{p}: {got!r} != {a!r}")
        e["edit_status"] = "ok" if not mismatches else "; ".join(mismatches)
        log("edit", rel, [(p, b, a) for p, b, a, _ in edits], e["edit_status"])
        save(state)


# ---------------------------------------------------------------- run
def do_run(state, only):
    for rel, e in state.items():
        if not wanted(rel, only):
            continue
        if not e.get("model_id") or e.get("sim_id"):
            continue
        r = S.post(
            f"{BASE}/api/v1/models/{e['model_id']}/simulate",
            json={"label": f"smoke {name_of(rel)}"},
            timeout=600,
        )
        e["simulate_http"] = r.status_code
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:300]}
        e["simulate_response"] = body
        e["sim_id"] = body.get("id")
        e["sim_submitted_at"] = time.time()
        log("simulate", rel, r.status_code, body.get("id") or body)
        save(state)


TERMINAL = {"completed", "succeeded", "failed", "errored", "cancelled"}


def wait_run(state, only, timeout=3600):
    pending = {rel for rel, e in state.items() if e.get("sim_id") and e.get("sim_status") not in TERMINAL and wanted(rel, only)}
    t0 = time.time()
    while pending and time.time() - t0 < timeout:
        for rel in sorted(pending):
            e = state[rel]
            r = S.get(f"{BASE}/api/v1/simulations/{e['sim_id']}", timeout=60)
            if r.status_code != 200:
                continue
            body = r.json()
            status = str(body.get("status", "")).lower()
            if status != e.get("sim_status"):
                log("status", rel, status)
            e["sim_status"] = status
            if status in TERMINAL:
                e["sim_seconds"] = round(time.time() - e.get("sim_submitted_at", t0))
                pending.discard(rel)
        save(state)
        if pending:
            time.sleep(15)
    for rel in pending:
        log("run timeout", rel)
    save(state)


# ---------------------------------------------------------------- check
def do_check(state, only):
    for rel, e in state.items():
        if not wanted(rel, only):
            continue
        sid = e.get("sim_id")
        if not sid:
            continue
        r = S.get(f"{BASE}/api/v1/simulations/{sid}/results", timeout=120)
        files = r.json() if r.status_code == 200 else []
        if isinstance(files, dict):
            files = files.get("artifacts") or files.get("files") or []
        e["artifacts"] = sorted({f.get("type") for f in files if isinstance(f, dict)})
        r = S.get(f"{BASE}/api/v1/simulations/{sid}/report", timeout=120)
        e["report_http"] = r.status_code
        if r.status_code == 200:
            rep = r.json()
            pfs = rep.get("per_feature_summary") or {}
            e["summary_counts"] = {k: len(v or {}) for k, v in pfs.items()}
            e["report_errors"] = (rep.get("errors") or [])[:3]
            e["report_warnings"] = len(rep.get("warnings") or [])
        edits = {x["kind"]: x for x in e.get("edits", [])}
        r = S.get(f"{BASE}/api/v1/simulations/{sid}/report-text", timeout=120)
        if r.status_code == 200:
            text = r.text if not r.headers.get("content-type", "").startswith("application/json") else str(r.json())
            step = edits.get("report_step", {}).get("after")
            e["rpt_has_edit"] = bool(step) and (f"Report Time Step ......... {step}" in text)
            e["rpt_errors"] = [ln.strip() for ln in text.splitlines() if "ERROR" in ln][:3]
        # The .inp the engine actually ran: source.inp rendered with the overlay.
        inp = next((f for f in files if isinstance(f, dict) and f.get("type") == "input"), None)
        url = (inp or {}).get("presignedUrl") or (inp or {}).get("url")
        geom = next((x for k, x in edits.items() if k.startswith("geom1:")), None)
        if url and geom:
            link = geom["kind"].split(":", 1)[1]
            body = requests.get(url, timeout=300).text
            in_xs = False
            found = None
            for ln in body.splitlines():
                if ln.strip().upper().startswith("[XSECTIONS]"):
                    in_xs = True
                    continue
                if in_xs and ln.strip().startswith("["):
                    break
                if in_xs and ln.split() and ln.split()[0] == link:
                    found = ln.split()
                    break
            e["rendered_geom1"] = found[2] if found and len(found) > 2 else None
            try:
                e["inp_has_edit"] = e["rendered_geom1"] is not None and float(e["rendered_geom1"]) == float(geom["after"])
            except ValueError:
                # Geom1 is a name for STREET/IRREGULAR shapes, not a number.
                e["inp_has_edit"] = f"n/a ({e['rendered_geom1']})"
        save(state)
        log("check", rel, e.get("sim_status"), e.get("artifacts"), "report", e.get("report_http"), "edit in rpt:", e.get("rpt_has_edit"), "geom1 in inp:", e.get("inp_has_edit"))


def report(state):
    print()
    print(f"{'file':52} {'parse':8} {'edit':6} {'run':10} {'report':6} {'zarr':5} {'edit→rpt':8}")
    for rel, e in state.items():
        print(
            f"{rel[:52]:52} {str(e.get('import_status', '-'))[:8]:8} {str(e.get('edit_status', '-'))[:6]:6} "
            f"{str(e.get('sim_status', '-'))[:10]:10} {str(e.get('report_http', '-')):6} "
            f"{'yes' if 'results_zarr' in (e.get('artifacts') or []) else 'no':5} {str(e.get('rpt_has_edit', '-')):8} {str(e.get('inp_has_edit', '-'))}"
        )


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    state = load()
    if stage in ("import", "all"):
        do_import(state, only)
        wait_import(state, only)
    if stage in ("edit", "all"):
        do_edit(state, only)
    if stage in ("run", "all"):
        do_run(state, only)
        wait_run(state, only)
    if stage in ("check", "all"):
        do_check(state, only)
    report(state)

#!/usr/bin/env python3
"""
NON-SLOP / backends.py
----------------------
The two sponsor integrations. Both are written against the published API
references and are DROP-IN: set the key, call the function, get a real verdict.

HONEST STATUS — read this before quoting anything downstream:
  Reducto : not called yet. No key in this environment. The account offers free
            credits on signup with no card, so this is one signup away.
  Pangram : not called yet. Developer API needs prepaid credits; the free web
            tier (2k words/day) is not the API. One key away.

Neither has been exercised against a live endpoint from this machine. The
request shapes below are taken from the vendors' own docs; the response
accessors are written defensively because we have not seen a real payload.
Nothing in the audit headline depends on either — the frame and anchor
measurements are computed locally and are fully reproducible without any key.
These layers exist to (a) admit artifacts the local engine cannot read at all,
and (b) check our metric against an independent detector.

  Pangram docs : https://docs.pangram.com/api-reference/ai-detection
  Reducto docs : https://docs.reducto.ai/parse/overview
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.error

TIMEOUT = 120


def _env(name: str) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    for p in ("/opt/data/.secrets/nonslop.env", "/opt/data/.secrets/sponsors.env"):
        if os.path.exists(p):
            for line in open(p):
                line = line.strip().removeprefix("export ")
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={**headers, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def _get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


# ---------------------------------------------------------------------------
# PANGRAM — "was this written by a machine?"
# ---------------------------------------------------------------------------

PANGRAM_BASE = "https://text.external-api.pangram.com"


def pangram_models(api_key: str | None = None) -> dict:
    """GET /models — the selectors this key is entitled to. Never hard-code."""
    return _get(f"{PANGRAM_BASE}/models", {"x-api-key": api_key or _env("PANGRAM_API_KEY")})


def pangram_score(text: str, api_key: str | None = None, model: str | None = None,
                  poll_s: float = 3.0, max_wait_s: int = 180) -> dict:
    """
    Submit one document, poll until done, return a normalised verdict.

    Normalised fields:
      ok, stage, ai_likelihood (0..1, higher = more machine-written),
      label ('AI'|'HUMAN'|'MIXED'|'UNKNOWN'), raw (vendor payload)
    """
    key = api_key or _env("PANGRAM_API_KEY")
    if not key:
        return {"ok": False, "error": "PANGRAM_API_KEY not set — see module docstring"}

    body = {"text": text[:200_000], "public_dashboard_link": False}
    if model:
        body["model"] = model
    else:
        try:
            body["model"] = (pangram_models(key).get("models") or ["pangram-4"])[0]
        except Exception:
            body["model"] = "pangram-4"

    task = _post(f"{PANGRAM_BASE}/task", body, {"x-api-key": key})
    tid = task.get("task_id") or task.get("id")
    if not tid:
        return {"ok": False, "error": "no task id in response", "raw": task}

    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        r = _get(f"{PANGRAM_BASE}/task/{tid}", {"x-api-key": key})
        stage = r.get("stage")
        if stage in ("STAGE_SUCCESS", "STAGE_FAILED"):
            break
        time.sleep(poll_s)

    # defensive extraction: we have not seen a live payload
    frac = (r.get("fraction_ai") or r.get("ai_fraction")
            or (r.get("prediction_short") or {}).get("fraction_ai"))
    if frac is None:
        frac = {"AI": 1.0, "HUMAN": 0.0, "MIXED": 0.5}.get(str(r.get("prediction")).upper())
    return {"ok": stage == "STAGE_SUCCESS" if stage else False, "stage": stage,
            "ai_likelihood": frac, "label": r.get("prediction"),
            "version": r.get("version"), "raw": r}


def pangram_bulk(texts: list[str], api_key: str | None = None) -> dict:
    """POST /bulk — 20% cheaper, use for whole-corpus sweeps (our 252 docs)."""
    key = api_key or _env("PANGRAM_API_KEY")
    if not key:
        return {"ok": False, "error": "PANGRAM_API_KEY not set"}
    return _post(f"{PANGRAM_BASE}/bulk", {"texts": texts, "model": "pangram-4"}, {"x-api-key": key})


# ---------------------------------------------------------------------------
# REDUCTO — makes non-text artifacts auditable, and locates slop per region
# ---------------------------------------------------------------------------

REDUCTO_BASE = "https://platform.reducto.ai"


def reducto_upload(path: str, api_key: str | None = None) -> dict:
    """POST /upload — local file -> file_id for /parse."""
    key = api_key or _env("REDUCTO_API_KEY")
    if not key:
        return {"ok": False, "error": "REDUCTO_API_KEY not set"}
    boundary = "----nonslop" + str(int(time.time()))
    data = open(path, "rb").read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + \
           f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{REDUCTO_BASE}/upload", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def reducto_parse(input_ref: str, api_key: str | None = None, page_range=None,
                  chunk_mode: str = "page") -> dict:
    """
    POST /parse — synchronous. input_ref is a public URL or a file_id from
    reducto_upload(). Requires ENTERPRISE-style access? No: /parse is the
    documented sync endpoint; /parse_async + /job/{id} for large documents.

    The layout boxes in the response are the point: they let us map slop to a
    REGION of a page rather than scoring the whole file. See spans_to_regions().
    """
    key = api_key or _env("REDUCTO_API_KEY")
    if not key:
        return {"ok": False, "error": "REDUCTO_API_KEY not set — free credits on signup, no card"}
    body = {"input": input_ref, "chunk_mode": chunk_mode}
    if page_range:
        body["page_range"] = page_range
    try:
        r = _post(f"{REDUCTO_BASE}/parse", body, {"Authorization": f"Bearer {key}"})
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:400]}
    return {"ok": True, "raw": r}


def spans_to_regions(spans: list[dict], parsed: dict) -> list[dict]:
    """
    Join our sentence-level frame classification to Reducto's layout boxes.

    spans  : [{'t': sentence, 'frame': bool, 'shared': float}]  from engine.py
    parsed : a Reducto /parse payload containing blocks with bboxes and text

    Returns [{text, frame, shared, page, bbox}] so the artifact can paint slop
    onto the actual geometry of a document instead of just its text stream.
    This is the capability the local engine does not have: a scanned report or a
    slide export has no readable text without Reducto, so it cannot be audited
    at all — and once it can be, you can see WHICH BOX on the page was inherited.
    """
    blocks = []
    for chunk in (parsed.get("result", {}) or {}).get("chunks", []) or parsed.get("chunks", []):
        for b in chunk.get("blocks", []) or []:
            blocks.append({"text": (b.get("content") or "").strip(),
                           "page": b.get("page") or chunk.get("page"),
                           "bbox": b.get("bbox")})
    out, bi = [], 0
    for s in spans:
        key = s["t"][:60].lower().replace(" ", "")
        match = None
        for i in range(bi, len(blocks)):
            if key and key in blocks[i]["text"].lower().replace(" ", ""):
                match = blocks[i]
                bi = i
                break
        out.append({"text": s["t"], "frame": s["frame"], "shared": s["shared"],
                    "page": (match or {}).get("page"), "bbox": (match or {}).get("bbox")})
    return out


if __name__ == "__main__":
    print(json.dumps({
        "PANGRAM_API_KEY": bool(_env("PANGRAM_API_KEY")),
        "REDUCTO_API_KEY": bool(_env("REDUCTO_API_KEY")),
        "pangram_sample_request": {
            "url": f"{PANGRAM_BASE}/task", "method": "POST",
            "headers": {"x-api-key": "<key>", "Content-Type": "application/json"},
            "body": {"text": "<document>", "model": "pangram-4", "public_dashboard_link": False},
            "then": f"GET {PANGRAM_BASE}/task/{{task_id}} until stage == STAGE_SUCCESS",
        },
        "reducto_sample_request": {
            "url": f"{REDUCTO_BASE}/parse", "method": "POST",
            "headers": {"Authorization": "Bearer <key>"},
            "body": {"input": "<url|file_id>", "chunk_mode": "page"},
        },
    }, indent=2))

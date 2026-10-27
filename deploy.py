#!/usr/bin/env python3
"""
Deploy site/ to Vercel as a static production deployment, via the REST API.
No CLI, no npm install. Reads VERCEL_TOKEN / VERCEL_TEAM_ID from .secrets.

Usage: python3 deploy.py [--name nobody-chose-this] [--dir site]
"""
import argparse, json, os, sys, urllib.request, urllib.error, mimetypes

SECRETS = "/opt/data/.secrets/vercel-d0xeddev.env"


def load_env(path):
    env = {}
    for line in open(path):
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def api(method, path, token, team=None, body=None):
    url = f"https://api.vercel.com{path}"
    if team:
        url += ("&" if "?" in url else "?") + f"teamId={team}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:900]
        raise SystemExit(f"HTTP {e.code} on {method} {path}\n{detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="nobody-chose-this")
    ap.add_argument("--dir", default="site")
    a = ap.parse_args()

    env = load_env(SECRETS)
    token = env.get("VERCEL_TOKEN")
    team = env.get("VERCEL_TEAM_ID")
    if not token:
        raise SystemExit("no VERCEL_TOKEN found")

    files = []
    for dirpath, _, filenames in os.walk(a.dir):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, a.dir)
            if fn.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")):
                import base64, hashlib
                raw = open(full, "rb").read()
                files.append({"file": rel, "data": base64.b64encode(raw).decode(),
                              "encoding": "base64",
                              "sha": hashlib.sha1(raw).hexdigest()})
            else:
                files.append({"file": rel, "data": open(full, encoding="utf-8").read()})

    print(f"[deploy] {len(files)} files, {sum(len(str(f.get('data',''))) for f in files)/1024:.0f} KB")

    # create the project first so the name is ours (idempotent)
    try:
        api("POST", "/v11/projects", token, team, {"name": a.name, "framework": None})
        print(f"[project] created {a.name}")
    except SystemExit as e:
        print(f"[project] exists or skipped: {str(e)[:160]}")

    res = api("POST", "/v13/deployments", token, team, {
        "name": a.name,
        "files": files,
        "target": "production",
        "projectSettings": {"framework": None, "buildCommand": None,
                            "outputDirectory": None, "installCommand": None},
    })
    url = res.get("url") or res.get("alias", [{}])[0].get("domain")
    print(json.dumps({"id": res.get("id"), "url": url, "ready": res.get("readyState"),
                      "aliases": res.get("alias")}, indent=2))
    print(f"\nLIVE: https://{url}")
    open("out/deploy.json", "w").write(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

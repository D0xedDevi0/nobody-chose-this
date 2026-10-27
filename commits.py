#!/usr/bin/env python3
"""
NON-SLOP / commits.py
---------------------
Second corpus. The agent has written 900+ commit messages. A commit message is
a claim about work. Reused commit frames are the cheapest possible slop: the
same sentence stamped onto unrelated days.

Reuses the exact masking + frame rules from engine.py so both corpora are
measured with one definition.
"""
import json, os, re, subprocess, statistics, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import tokens, sent_shingles, anchor_count  # noqa: E402


def git_log(repo: str, limit: int = 1200) -> list[dict]:
    fmt = "%H%x1f%ai%x1f%s%x1f%b%x1e"
    out = subprocess.run(
        ["git", "-C", repo, "log", f"--max-count={limit}", f"--pretty=format:{fmt}"],
        capture_output=True, text=True, check=True).stdout
    rows = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        parts = rec.split("\x1f")
        if len(parts) < 3:
            continue
        sha, date, subj = parts[0], parts[1], parts[2]
        body = parts[3] if len(parts) > 3 else ""
        rows.append({"sha": sha[:10], "date": date[:10], "subject": subj.strip(),
                     "body": body.strip()[:600]})
    return rows


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/D0XEDDEV"
    out = sys.argv[2] if len(sys.argv) > 2 else "out/commits.json"
    rows = git_log(repo)
    print(f"[git] {len(rows)} commits")

    # frame analysis: normalise each subject to masked tokens, count cross-commit reuse
    keys = {}
    df = Counter()
    for r in rows:
        # mask trailing specifics (issue numbers, versions, paths) but keep the verb frame
        k = " ".join(tokens(r["subject"]))
        k = re.sub(r"(<issue>|<num>|<ver>|<hash>|<addr>|<ticker>|<qty>|<money>)+", "<x>", k)
        keys[r["sha"]] = k
        df[k] += 1

    # subject class: what kind of claim is this?
    TYPE_RX = {
        "feat": r"^\s*(feat|feature|add|implement|introduce|new)\b",
        "fix": r"^\s*(fix|bugfix|patch|hotfix|revert|resolve)\b",
        "chore": r"^\s*(chore|bump|deps|cleanup|tidy|refactor|rename|move|lint|format)\b",
        "docs": r"^\s*(docs?|readme|comment)\b",
        "ops": r"^\s*(deploy|ci|ops|cron|monitor|health|guard|harden)\b",
        "data": r"^\s*(log|record|snapshot|digest|update data|sync|state)\b",
        "agent": r"^\s*(agent|devio|social|post|tweet|x:)\b",
    }
    def kind(s):
        for k, rx in TYPE_RX.items():
            if re.search(rx, s, re.I):
                return k
        if re.match(r"^(alpha|trench|wave|mentions|scan|intel|digest)", s, re.I):
            return "data"
        return "other"

    for r in rows:
        r["kind"] = kind(r["subject"])
        r["frame_key"] = keys[r["sha"]]
        r["template"] = df[keys[r["sha"]]] >= 3
        r["anchors"] = sum(anchor_count(r["subject"] + " " + r["body"])[1].values())
        r["words"] = len(r["subject"].split()) + len(r["body"].split())
        r["empty_body"] = len(r["body"].split()) < 3

    kinds = Counter(r["kind"] for r in rows)
    templated = [r for r in rows if r["template"]]
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["frame_key"], []).append(r)

    # the frames used most, with a representative and its span of dates
    top_frames = sorted((g for g in groups.values() if len(g) >= 3), key=lambda g: -len(g))[:40]
    frames_out = [{
        "n": len(g),
        "sample": g[0]["subject"][:160],
        "first": min(x["date"] for x in g),
        "last": max(x["date"] for x in g),
        "kinds": dict(Counter(x["kind"] for x in g)),
        "shas": [x["sha"] for x in g[:6]],
    } for g in top_frames]

    empty = [r for r in rows if r["empty_body"]]
    data = {
        "commits": len(rows),
        "first": rows[-1]["date"] if rows else None,
        "last": rows[0]["date"] if rows else None,
        "kinds": dict(kinds),
        "templated_commits": len(templated),
        "templated_share": round(len(templated) / max(1, len(rows)), 4),
        "distinct_frames": len(groups),
        "frames_used_3plus": len(top_frames),
        "single_use_frames": sum(1 for g in groups.values() if len(g) == 1),
        "empty_body_commits": len(empty),
        "empty_body_share": round(len(empty) / max(1, len(rows)), 4),
        "mean_words": round(statistics.fmean(r["words"] for r in rows), 1),
        "mean_anchors": round(statistics.fmean(r["anchors"] for r in rows), 2),
        "top_frames": frames_out,
        "recent": [{"sha": r["sha"], "date": r["date"], "subject": r["subject"][:180],
                    "kind": r["kind"], "template": r["template"], "words": r["words"]} for r in rows[:120]],
    }
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump(data, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in data.items() if k not in ("top_frames", "recent")}, indent=2))
    print("\ntop commit frames:")
    for f in frames_out[:10]:
        print(f"  x{f['n']:<4} {f['first']}→{f['last']}  {f['sample'][:90]}")


if __name__ == "__main__":
    main()

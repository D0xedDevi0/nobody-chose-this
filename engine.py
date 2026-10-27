#!/usr/bin/env python3
"""
NON-SLOP / engine.py  (v2)
--------------------------
A reproducible slop audit of an AI agent's own written output.

THESIS
  Slop is not bad writing. Slop is a decision nobody made.

  Generation is free now. What is scarce is the act of choosing — and a choice
  leaves a trace you can count. Two traces, in fact:

  1. THE FRAME  A sentence whose word-sequence already existed verbatim in other
                documents was not written for *this* document. It was inherited.
                Measure: share of a sentence's 5-grams that appear in >= 3 other
                documents, on entity-masked text (numbers/tickers/handles/dates
                replaced by slots, so "price rose 4%" and "price fell 9%" are the
                SAME frame — which is precisely the failure being audited).

  2. THE CONTENT  A sentence earns its place by carrying verifiable anchors:
                  URLs, handles, tickers, CVE ids, issue numbers, versions,
                  quantities with units, currency, addresses, quoted strings,
                  code identifiers. Anchors are the fingerprint of a decision.

  A document that is mostly frame, with little anchor density in the part of it
  that is not frame, contains almost no decisions. That is the definition this
  audit uses, it is stated up front, and anyone can re-run it.

  No paid API is required to reproduce a single number below.
  Optional authoritative layers live in backends.py:
    Pangram -> replaces the local style proxy with a real AI-text verdict
    Reducto -> parses PDF/scan/image artifacts so they can be audited at all,
               and returns layout boxes so slop can be located per REGION.

stdlib only. Deterministic. Re-runnable: python3 engine.py --root <dir>
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, statistics, sys
from collections import Counter

# ---------------------------------------------------------------------------
# 1. corpus definition  (stated, not assumed)
# ---------------------------------------------------------------------------

DOC_RX = re.compile(r"\.(md|mdx|markdown|rst|txt)$", re.I)
MEDIA_RX = re.compile(r"\.(png|jpe?g|webp|gif|mp4|mov|webm|pdf|pptx?|docx?|xlsx?)$", re.I)

# Directories that hold other people's prose. Auditing an agent on the text of
# its dependencies would be dishonest, so they are excluded by name.
EXCLUDE_DIR = {
    "node_modules", ".git", ".next", "dist", "build", "cache", "__pycache__",
    ".venv", "venv", "env", "site-packages", "lib", "vendor", "third_party",
    "third-party", "submodules", "assets", "public", "coverage", ".turbo",
}
# Files that are not authored prose at all.
EXCLUDE_FILE = re.compile(r"^(license|licence|notice|copying|changelog|authors|contributors|patents)",
                          re.I)
DATE_IN_NAME = re.compile(r"[-_ ]?\d{4}[-_ ]?\d{2}[-_ ]?\d{2}")

# ---------------------------------------------------------------------------
# 2. masking  ->  the reusable prose frame
# ---------------------------------------------------------------------------

MASK = [
    (re.compile(r"https?://\S+"), " <url> "),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), " <email> "),
    (re.compile(r"\b(?:CVE|GHSA)-\d{4}-\d{4,7}\b", re.I), " <cve> "),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?\b"), " <date> "),
    (re.compile(r"\b0x[0-9a-fA-F]{6,}\b"), " <addr> "),
    (re.compile(r"\b[0-9a-f]{7,40}\b"), " <hash> "),
    (re.compile(r"\bv?\d+\.\d+(?:\.\d+)*\b"), " <ver> "),
    (re.compile(r"\$[A-Za-z][A-Za-z0-9_]{1,9}\b"), " <ticker> "),
    (re.compile(r"@[A-Za-z0-9_]{2,15}\b"), " <handle> "),
    (re.compile(r"#\d{1,6}\b"), " <issue> "),
    (re.compile(r"\b\d[\d,._]*\s?(?:%|x|h|hrs?|d|days?|wks?|weeks?|mins?|s|ms|mb|gb|kb|tokens?|words?|users?|pages?|usd|eth)\b", re.I), " <qty> "),
    (re.compile(r"[$€£]\s?\d[\d,._]*"), " <money> "),
    (re.compile(r"\b\d[\d,._]*\b"), " <num> "),
]


def mask(text: str) -> str:
    t = text.lower()
    for rx, rep in MASK:
        t = rx.sub(rep, t)
    t = re.sub(r"[^a-z<> ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


DOM = r"<url>|<email>|<cve>|<date>|<addr>|<hash>|<ver>|<ticker>|<handle>|<issue>|<qty>|<money>|<num>"
TOK_RX = re.compile(rf"(?:{DOM})|[a-z]+")


def tokens(text: str) -> list[str]:
    return TOK_RX.findall(mask(text))


def sentences(text: str) -> list[str]:
    """Split on sentence enders and markdown bullets/headings — each is a unit."""
    t = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    t = re.sub(r"^\s*#{1,6}\s+", "", t, flags=re.M)
    t = re.sub(r"\n{2,}", "\n", t)
    parts = re.split(r"(?<=[.!?:])\s+|\n", t)
    return [p.strip() for p in parts if len(p.split()) >= 4]


# ---------------------------------------------------------------------------
# 3. anchors  ->  the fingerprint of a decision
# ---------------------------------------------------------------------------

ANCHOR_RX = {
    "url":    re.compile(r"https?://\S+"),
    "handle": re.compile(r"(?<![\w.])@[A-Za-z0-9_]{2,15}\b"),
    "ticker": re.compile(r"\$[A-Za-z][A-Za-z0-9_]{1,9}\b"),
    "cve":    re.compile(r"\b(?:CVE|GHSA)-\d{4}-\d{4,7}\b", re.I),
    "issue":  re.compile(r"#\d{1,6}\b"),
    "ver":    re.compile(r"\bv?\d+\.\d+(?:\.\d+)*\b"),
    "date":   re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}\b"),
    "qty":    re.compile(r"\b\d[\d,._]*\s?(?:%|x|h|hrs?|d|days?|wks?|weeks?|mins?|mb|gb|kb|tokens?|words?|users?|pages?|usd|eth)\b", re.I),
    "money":  re.compile(r"[$€£]\s?\d[\d,._]*"),
    "addr":   re.compile(r"\b0x[0-9a-fA-F]{6,}\b"),
    "path":   re.compile(r"\b[\w.-]+/[\w./-]{3,}\b"),
    "code":   re.compile(r"`[^`\n]{2,}`|\b[a-z_][a-z0-9_]{2,}\([^)\n]{0,80}\)"),
}

FILLER = set("""leverage seamless robust comprehensive holistic pivotal crucial vital empower unlock
foster navigate landscape realm tapestry testament delve underscore highlight showcase elevate
streamline optimize synergy ecosystem paradigm innovative cutting-edge transformative
furthermore moreover additionally ultimately essentially significantly notably importantly
reimagining revolutionizing democratizing enabling driving shaping powering fueling
insights intelligence framework platform solution approach journey mission vision""".split())
HEDGE_RX = re.compile(r"\b(it'?s worth noting|needless to say|at the end of the day|"
                      r"in today'?s (?:fast-paced|ever-changing|rapidly evolving)|"
                      r"let'?s dive in|game[- ]chang\w+|unlock\w* the (?:power|potential)|"
                      r"we'?re excited to|stay tuned)\b", re.I)


def anchor_count(text: str) -> tuple[int, dict]:
    hits = {k: len(rx.findall(text)) for k, rx in ANCHOR_RX.items()}
    return sum(hits.values()), hits


# ---------------------------------------------------------------------------
# 4. harvest
# ---------------------------------------------------------------------------

def harvest(root: str, max_docs: int, min_words: int):
    docs, media, skipped = [], Counter(), Counter()
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if any(p in EXCLUDE_DIR for p in rel_dir.split(os.sep)):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR and not d.startswith(".git")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if MEDIA_RX.search(fn):
                media[os.path.splitext(fn)[1].lower()] += 1
                continue
            if not DOC_RX.search(fn) or EXCLUDE_FILE.match(fn):
                skipped["not_prose"] += 1
                continue
            try:
                raw = open(full, encoding="utf-8", errors="ignore").read(300_000)
            except OSError:
                skipped["unreadable"] += 1
                continue
            w = len(mask(raw).split())
            if w < min_words:
                skipped["too_short"] += 1
                continue
            sents = sentences(raw)
            if len(sents) < 3:
                skipped["too_few_sentences"] += 1
                continue
            stem = DATE_IN_NAME.sub("", os.path.splitext(fn)[0]).strip("-_ ") or fn
            docs.append({
                "path": os.path.relpath(full, root), "file": fn, "series": stem,
                "words": w, "bytes": os.path.getsize(full), "sents": sents,
                "sha": hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:12],
                "head": raw.strip()[:300],
            })
            if len(docs) >= max_docs:
                del dirnames[:]
                break
    return docs, {"media": dict(media), "skipped": dict(skipped)}


# ---------------------------------------------------------------------------
# 5. the two measurements
# ---------------------------------------------------------------------------

def sent_shingles(s: str, n: int = 5) -> set[str]:
    t = tokens(s)
    return {" ".join(t[i:i + n]) for i in range(max(0, len(t) - n + 1))}


def audit_corpus(docs, df_min: int = 3, frame_threshold: float = 0.60):
    """Return per-document + per-sentence frame/content classification."""
    sent_grams, df = [], Counter()
    for d in docs:
        row = []
        for s in d["sents"]:
            g = sent_shingles(s)
            row.append(g)
            df.update(g)
        sent_grams.append(row)

    results = []
    for d, grams_per_sent in zip(docs, sent_grams):
        all_grams = set().union(*grams_per_sent) if grams_per_sent else set()
        reused_prose = (sum(1 for g in all_grams if df[g] >= df_min) / len(all_grams)) if all_grams else 0.0

        spans, frame_words, content_words = [], 0, 0
        content_text = []
        for s, g in zip(d["sents"], grams_per_sent):
            shared = (sum(1 for x in g if df[x] >= df_min) / len(g)) if g else 0.0
            is_frame = shared >= frame_threshold
            nw = len(s.split())
            spans.append({"t": s[:400], "frame": is_frame, "shared": round(shared, 3), "w": nw})
            if is_frame:
                frame_words += nw
            else:
                content_words += nw
                content_text.append(s)

        total = max(1, frame_words + content_words)
        content_joined = " ".join(content_text)
        n_anch, anchor_hits = anchor_count(content_joined)
        # ANCHOR DENSITY OF THE ORIGINAL PART ONLY. A document that is all frame
        # has no original part, so its content specificity is 0 by construction.
        content_density = round(n_anch / content_words * 1000, 2) if content_words else 0.0
        whole_anch, _ = anchor_count(" ".join(d["sents"]))
        filler = sum(content_joined.lower().count(w) for w in FILLER)

        frame_share = round(frame_words / total, 4)
        slop = round(min(100.0, 100 * (0.70 * frame_share + 0.30 * max(0.0, 1 - min(content_density, 40) / 40))), 1)

        v, why = classify(frame_share, content_density, reused_prose)
        results.append({
            "path": d["path"], "file": d["file"], "series": d["series"],
            "bytes": d["bytes"], "words": d["words"], "sha": d["sha"],
            "reused_prose": round(reused_prose, 4),
            "frame_share": frame_share,
            "frame_words": frame_words, "content_words": content_words,
            "content_anchor_density": content_density,
            "whole_anchor_density": round(whole_anch / max(1, d["words"]) * 1000, 2),
            "filler_density": round(filler / max(1, content_words) * 1000, 2),
            "anchors": anchor_hits,
            "slop_index": slop, "verdict": v, "why": why,
            "spans": spans,
            "head": d["head"],
        })
    results.sort(key=lambda r: -r["slop_index"])
    return results, df


def classify(frame_share: float, content_density: float, reused: float):
    if frame_share >= 0.75:
        return "TEMPLATE", "Three quarters of this document was inherited. The frame made the choices."
    if frame_share >= 0.45 and content_density < 10:
        return "THIN", "Reused scaffolding wrapped around very little that is checkable."
    if content_density < 6 and frame_share < 0.45:
        return "VAPOUR", "Original wording, nothing verifiable inside it."
    if frame_share <= 0.25 and content_density >= 25:
        return "SURVIVOR", "Little inherited, densely anchored. This one had to exist."
    return "PASSABLE", "Some choices were made here."


def repeated_sentences(df: Counter, docs, df_min: int = 4, limit: int = 40):
    """The money shot: sentences written once and published many times."""
    canon: dict[str, str] = {}
    counts: Counter = Counter()
    for d in docs:
        seen = set()
        for s in d["sents"]:
            key = " ".join(tokens(s))
            if len(key.split()) < 6:
                continue
            if key not in canon:
                canon[key] = s[:300]
            if key not in seen:
                counts[key] += 1
                seen.add(key)
    out = [{"text": canon[k], "documents": c} for k, c in counts.most_common() if c >= df_min]
    return out[:limit]


# ---------------------------------------------------------------------------
# 6. main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="out/audit.json")
    ap.add_argument("--max-docs", type=int, default=400)
    ap.add_argument("--min-words", type=int, default=60)
    a = ap.parse_args()

    docs, inv = harvest(a.root, a.max_docs, a.min_words)
    print(f"[harvest] {len(docs)} agent-authored text artifacts; binary artifacts: {inv['media']}",
          file=sys.stderr)
    res, df = audit_corpus(docs)
    by_v = Counter(r["verdict"] for r in res)
    reps = repeated_sentences(df, docs)

    series: dict[str, list] = {}
    for r in res:
        series.setdefault(r["series"], []).append(r)
    multi = {s: v for s, v in series.items() if len(v) >= 3}

    frame_words = sum(r["frame_words"] for r in res)
    total_words = sum(r["words"] for r in res)

    audit = {
        "thesis": "Slop is not bad writing. Slop is a decision nobody made.",
        "method": {
            "corpus_rule": "agent-authored .md/.mdx/.rst/.txt prose >= 60 words; vendored libraries, "
                           "licences, node_modules and asset dirs excluded by name",
            "frame_rule": "a sentence is FRAME when >=60% of its 5-grams (entity-masked: numbers, "
                          "tickers, handles, dates, versions, CVEs collapsed to slots) already appear "
                          "in at least 3 other documents",
            "anchor_rule": "verifiable anchors = urls, handles, tickers, CVE ids, issue numbers, "
                           "semver, dates, quantities with units, currency, 0x addresses, paths, code",
            "specificity_rule": "anchor density per 1,000 words measured over NON-FRAME sentences only, "
                                "so a document made entirely of inherited text scores 0 by construction",
            "reproduce": "python3 engine.py --root <repo>",
        },
        "corpus": {
            "root": a.root,
            "text_artifacts": len(res),
            "words_audited": total_words,
            "binary_artifacts": inv["media"],
            "binary_note": "binary artifacts are not scored. Reducto is the layer that makes them "
                           "auditable at all, and its layout boxes are what let slop be located per region",
            "excluded": inv["skipped"],
        },
        "headline": {
            "frame_words": frame_words,
            "frame_word_share": round(frame_words / max(1, total_words), 4),
            "repeated_series": len(multi),
            "template_docs": by_v.get("TEMPLATE", 0),
            "survivor_docs": by_v.get("SURVIVOR", 0),
            "mean_frame_share": round(statistics.fmean(r["frame_share"] for r in res), 4),
            "mean_content_density": round(statistics.fmean(r["content_anchor_density"] for r in res), 2),
            "sentences_published_more_than_once": len(reps),
            "max_sentence_reuse": reps[0]["documents"] if reps else 0,
        },
        "verdicts": dict(by_v),
        "repeated_sentences": reps,
        "series": {s: {"n": len(v),
                       "mean_frame": round(statistics.fmean(x["frame_share"] for x in v), 3),
                       "mean_slop": round(statistics.fmean(x["slop_index"] for x in v), 1),
                       "words": sum(x["words"] for x in v)}
                   for s, v in sorted(multi.items(), key=lambda kv: -len(kv[1]))},
        "documents": res,
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(audit, open(a.out, "w"), indent=1)

    print(json.dumps(audit["headline"], indent=2))
    print("verdicts:", dict(by_v))
    print("\nworst 10:")
    for r in res[:10]:
        print(f"  {r['slop_index']:5.1f} frame={r['frame_share']:5.0%} content={r['content_anchor_density']:6.1f}/1k "
              f"{r['verdict']:9} {r['file'][:50]}")
    print("best 5:")
    for r in res[-5:]:
        print(f"  {r['slop_index']:5.1f} frame={r['frame_share']:5.0%} content={r['content_anchor_density']:6.1f}/1k "
              f"{r['verdict']:9} {r['file'][:50]}")

    print("\ntop repeated sentences:")
    for r in reps[:6]:
        print(f"  x{r['documents']:<4} {r['text'][:110]}")

    # ---- trimmed payload for the published artifact -----------------------
    keep_spans = {r["path"] for r in res[:6]} | {r["path"] for r in res[-4:]}
    big = sorted((r for r in res if r["series"] in multi), key=lambda r: -len(series[r["series"]]))[:3]
    keep_spans |= {r["path"] for r in big}
    # the most instructive map is a MIXED document: frame and content sentences
    # interleaved in one file. Pick the one closest to a half-and-half split.
    mixed = sorted((r for r in res if len(r["spans"]) >= 14 and r["words"] >= 150
                    and 0.20 <= r["frame_share"] <= 0.70),
                   key=lambda r: abs(r["frame_share"] - 0.45))
    if mixed:
        keep_spans.add(mixed[0]["path"])
        print(f"[exemplar] mixed document: {mixed[0]['file']} frame={mixed[0]['frame_share']:.0%}")
    site = json.loads(json.dumps(audit))
    site["documents"] = [{
        **{k: v for k, v in r.items() if k not in ("spans", "head")},
        "head": r["head"][:180],
        **({"spans": r["spans"][:70]} if r["path"] in keep_spans else {}),
    } for r in res]
    out_site = os.path.join(os.path.dirname(a.out) or ".", "site-data.json")
    json.dump(site, open(out_site, "w"), separators=(",", ":"))
    print(f"\n[wrote] {a.out}  ({os.path.getsize(a.out)/1024:.0f} KB)")
    print(f"[wrote] {out_site}  ({os.path.getsize(out_site)/1024:.0f} KB)")


if __name__ == "__main__":
    main()

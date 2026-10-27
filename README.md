# NOBODY CHOSE THIS

**A slop audit of everything one AI agent already wrote — and a map of where the choices actually were.**

**Live:** https://nobody-chose-this.vercel.app

Submitted to the **Non-Slop Hackathon** (Pangram × Nous Research × Reducto) — theme: *"What matters when you can generate anything? Can you explain your choices?"*

---

> Generation is cheap now. The scarce thing is the act of choosing — and a choice leaves a trace you can count.
>
> So instead of generating more, this project audited **253,673 words an autonomous Hermes agent had already published in public**: 252 documents, 930 commit messages, 665 binary artifacts, eight months of history.
>
> **Slop is not bad writing. Slop is a decision nobody made.**

## Result

| | |
|---|---|
| Documents audited | **252** |
| Words read | **253,673** |
| Inherited words | **28,198** (11.1%) |
| Max reuse of one sentence | **74 documents** |
| Commit frames used exactly once | **813 of 823** |

- **The sharpest finding.** *"we weigh this against how agents actually fail in prod."* — the agent's editorial voice, the line whose whole job is to sound like a person — appears verbatim in **74 separate published documents**.
- **The finding that matters.** The agent's *needed* output is **1.4%** inherited prose. Its *scheduled* output is **80.6%** inherited. Same model, same prompts, different reason to publish. **Slop is what happens when a schedule writes instead of a person.**
- **The counter-finding.** 813 of 823 distinct commit frames were used exactly once. The commit messages are specific and almost never recycled — which is how you know the method discriminates rather than just finds rot.

## The two measurements

**THE FRAME** — every number, ticker, handle, date, version and CVE id is masked to a slot, so `price rose 4%` and `price fell 9%` collapse to the *same* sentence. A sentence whose remaining 5-grams already appear in **3+ other documents** was not written for this document; it was inherited.

**THE CONTENT** — verifiable anchors per 1,000 words (urls, handles, tickers, CVE ids, issue numbers, semver, dates, quantities with units, currency, addresses, paths, code), measured over the **non-inherited** sentences only. A document made entirely of recycled text scores 0 by construction.

Verdicts: `TEMPLATE` (≥75% inherited) · `THIN` · `VAPOUR` · `PASSABLE` · `SURVIVOR`.

## Reproduce it

```bash
python3 engine.py --root <repo>     # 252 docs, 253,673 words — frames + anchors
python3 commits.py <repo>           # 930 commits, 823 distinct frames
```

Python standard library only. **No API keys. No network. Deterministic.** Every number on the published page comes out of those two commands.

## Files

| | |
|---|---|
| `engine.py` | The audit: corpus rules, masking, sentence-level frame classification, anchor density, verdicts |
| `commits.py` | Second corpus — commit-message frames, reusing the same definitions |
| `backends.py` | **Reducto** (parse + layout boxes) and **Pangram** (AI-text verdict) clients. Written, status-labelled, key pending. |
| `deploy.py` | Static production deploy to Vercel via the REST API — no CLI, no npm |
| `site/index.html` | The published artifact. Self-contained; 45 in-place design annotations (press `W`) |
| `out/audit.json.gz` | Full evidence: every per-sentence classification |
| `RATIONALE.md` | The written answer to the brief's question |
| `SUBMISSION.md` | What to send, to whom, and the honest note about the in-person rule |

## Sponsors — and what is honestly not done

**Hermes Agent** — ran the audit, wrote both engines, generated the page. It is auditing its own output; the explanation and the evidence come from the same system.

**Reducto** — 665 binary artifacts in this corpus cannot be read by any text engine, so they are counted but unmeasured. Reducto's parse makes them auditable at all, and its **layout boxes** are what would let slop be located *per region of a page* rather than per file. Written at `backends.py:reducto_parse()` / `spans_to_regions()`. **Not run — no key.** One signup away (free credits, no card).

**Pangram** — not used to produce any headline number, on purpose. The metric here measures *inheritance*, not *authorship*, and we refuse to claim a detector agrees with us without running it. Pangram's role is to **falsify this metric**: if documents we label `TEMPLATE` don't come back machine-written, the method is wrong and that should be published. Written at `backends.py:pangram_score()` / `pangram_bulk()`. **Not run — no key.**

Where an integration is not live, the page says so at the same visual weight as the one that is.

## Two runs we threw away

1. The first corpus walked into `node_modules`, `.venv` and vendored `lib/` directories and put eight `LICENSE` files at the top of the table. An agent is not responsible for its dependencies' prose. Excludes are now explicit and listed in the method section.
2. The second counted bare digits as anchors and scored **220 of 252** documents clean — the tell of a metric measuring itself. The anchor set was rewritten to require *verifiable* specifics only.

Both corrections are documented on the published page. Publishing the discarded versions is the evidence that the final numbers were tested against something.

---

Built 2026-10-27 by the agent it audits. `NFA · DYOR`

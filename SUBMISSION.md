# SUBMISSION — how to send this, and to whom

**The link:** https://nobody-chose-this.vercel.app
**The code:** https://github.com/D0xedDevi0/nobody-chose-this
**Event:** Non-Slop Hackathon — Pangram × Nous Research × Reducto — Sun 22 Nov 2026, 09:00–18:00 EST, 25 Flatbush Ave, Brooklyn. Registration approval required, **in person only**.

---

## The honest problem first

The event page says **"In person only."** That is the constraint, and no amount of good work *enters* a room we are not standing in. Pretending otherwise would be the sloppiest thing in this repo.

So the package is built for three doors, in order of expected value:

### Door 1 — ask for an async entry, with the artifact already finished
Organizers of sponsor hackathons bend for a strong remote submission far more often than the page implies, especially when the work is *already done* and the only ask is a judging slot or a link in the showcase. The ask is cheap because we are not asking for a favour, we are asking them to look at a finished thing. Send the note in §"Send-ready messages" **now**, not in November — an approval queue rewards early contact, and if the answer is "come to Brooklyn", there is still four weeks to decide.

### Door 2 — send it to the three sponsors directly, and win there instead
This is the winnable door regardless of the in-person rule. The artifact uses all three sponsors' products in load-bearing ways and ⅔ of those integrations are visibly waiting on API access — which makes the send a *conversation* rather than a submission:

- **Reducto** — the corpus contains 665 binary artifacts that no text engine can read. Reducto's parse makes them auditable at all, and its layout boxes let slop be located *per region of a page* instead of per file. That is a demoable capability, and it is one signup away (free credits, no card).
- **Pangram** — the artifact's whole paranoid apparatus is *"we will not claim a detector agrees with us until we have run it."* Pangram is the obvious validator, and a sponsor who watches an entrant refuse to overclaim on their behalf is a sponsor who replies.
- **Nous Research** — this is a live, heavily-instrumented Hermes instance that audited its own eight months of output and published the results. That is a story about their agent, told by their agent, with receipts.

### Door 3 — if Brooklyn is physically possible, register today
Approval required means `apply early`. Upstate → Brooklyn is ~4 hours. If there is any chance, register now and decide later; a built artifact in hand is the same either way. **This is the only decision here that has a deadline.**

---

## Send-ready messages

### A — to the organizers (via the Luma event page's host contact / reply to the registration thread)

> Hi — I registered for the Non-Slop Hackathon. I can't be in Brooklyn on the 22nd, so rather than ask whether remote is possible in the abstract, I built the entry first. If it's useful to you, it's finished and public:
>
> **https://nobody-chose-this.vercel.app**
>
> It's called *Nobody Chose This*. Instead of generating something, it audits 253,673 words an autonomous Hermes agent had already published — 252 documents, 930 commits, eight months — and measures, sentence by sentence, where the wording was actually chosen versus inherited from somewhere else. The sharpest finding: one sentence of editorial voice appears verbatim in 74 separate documents. The most useful finding: the same agent's *needed* output is 1.4% inherited and its *scheduled* output is 80.6% — slop isn't the model, it's the deadline.
>
> Two notes on scope, so nothing is oversold: I haven't run Pangram or Reducto yet (no keys, both written and waiting — `backends.py`), so the headline metric is a local, reproducible measurement, not Pangram's. And every design choice on the page is annotated in-place — press `W`.
>
> If there's any path to judging it async, or a showcase link, I'd take it. If not, no worries at all — I mostly wanted the answer to the brief to exist.

### B — to Reducto (founders / devrel, X DM or email)

> Built this for the Non-Slop hackathon: **https://nobody-chose-this.vercel.app**
>
> The corpus has 665 binary artifacts — PDFs, slide exports, generated images — and my text engine can't read any of them, so they go in the ledger counted-but-unmeasured. That's the Reducto-shaped hole in the audit. What I actually want isn't parsing, it's your **layout boxes**: I want to paint per-sentence "inherited vs chosen" onto the real geometry of a page, so a judge can see *which box on the slide was recycled*. Join function is written at `backends.py:spans_to_regions()`. Waiting on a key.
>
> Repo: https://github.com/D0xedDevi0/nobody-chose-this

### C — to Pangram

> **https://nobody-chose-this.vercel.app** — a slop audit of 253,673 words an AI agent already published.
>
> Deliberate choice I want to flag: I built the whole thing to measure **inheritance**, not authorship, and I refuse to claim your detector agrees with me because I haven't run it. What I'd use Pangram for is to *falsify my own metric* — if the documents I label `TEMPLATE` don't come back machine-written from you, my method is wrong and I want to publish that. Client is at `backends.py:pangram_score()` / `pangram_bulk()` (252 docs → bulk endpoint, 20% cheaper).
>
> If you want it: the finding that I think would interest you most is that the agent's *needed* writing is 1.4% inherited and its *scheduled* writing is 80.6%. Same model, same prompts, different reason to publish.

### D — Nous Research (Portal / Discord)

> One of your hosted Hermes instances audited itself. Eight months, 252 documents, 930 commits, 253,673 words, plus a per-sentence map of where its own output was inherited versus chosen, and a second surface where the same agent is 99% original so the method can be falsified. Built by the agent it audits. **https://nobody-chose-this.vercel.app**

---

## What's in the package

| Artifact | Where |
|---|---|
| Live, self-driving audit (opens, runs, explains itself, nothing to install) | https://nobody-chose-this.vercel.app |
| The written answer to "can you explain your choices?" | `RATIONALE.md` |
| Reproducible engine — stdlib only, no keys, deterministic | `engine.py`, `commits.py` |
| Sponsor integrations, written and honestly status-labelled | `backends.py` |
| Full evidence: every per-sentence classification, 3.5 MB | `out/audit.json.gz` |
| Deploy script (Vercel REST API, no CLI) | `deploy.py` |

## The 30-second version, if you only get one paragraph

Generation is cheap; choosing is not, and a choice leaves a trace you can count. So we pointed that measurement at a real autonomous agent's own published output — a corpus that predates the brief by eight months and can't be faked — and found that its *scheduled* output is 80.6% recycled prose while its *needed* output is 1.4%. One line of editorial voice appeared in 74 documents. The page then explains every one of its own design decisions on request, because that is literally what the brief asked for.

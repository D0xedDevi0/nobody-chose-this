# Can you explain your choices?

The brief was: *what matters when you can generate anything? Can you explain your choices?*

This is our attempt at an answer that is checkable rather than tasteful-sounding. It is also the thing that was itself the hardest to write honestly, because the honest version says the system is wrong in places.

**Live artifact:** https://nobody-chose-this.vercel.app

---

## 1. The claim

> **Slop is not bad writing. Slop is a decision nobody made.**

When generation is free, the scarce act is choosing. A choice leaves evidence: it names a specific thing, a quantity, a constraint, a path, a date. Text that was *not* chosen leaves the opposite evidence — its wording already existed somewhere else, and swapping the nouns produces a different document.

Both traces are countable. That is the whole project.

## 2. Why this instead of generating something

Because generating something is the cheap move, and the brief says so out loud: *"aesthetics can now be generated cheaply."* Adding one more beautiful artifact to a room full of generated artifacts answers the wrong half of the question.

So we did not generate. We went back through **253,673 words an autonomous agent had already published in public** — 252 documents, 930 commit messages, 665 binary artifacts — and audited them.

That has three consequences we wanted:

- **It cannot be faked.** The corpus predates the brief by eight months. Every finding is a fact about a real repository with real dates and real SHAs.
- **It is falsifiable.** Anyone can clone the repo, run `engine.py`, and get the same numbers. If our metric is bad, that is visible rather than arguable.
- **It costs us something.** The worst findings are about our own pipeline. An audit that only finds rot is a prosecution with a method.

## 3. The two measurements

**THE FRAME.** Mask every number, ticker, handle, date, version and CVE id to a slot — so `price rose 4%` and `price fell 9%` collapse to the *same* sentence. That is deliberate: it makes the mask measure the reusable prose frame and nothing else. A sentence whose remaining 5-word sequences already appear in **3 or more other documents** was not written for this document. It was inherited.

**THE CONTENT.** Verifiable anchors per 1,000 words — urls, handles, tickers, CVE ids, issue numbers, semver, dates, quantities with units, currency, addresses, paths, code. Measured **over the non-inherited sentences only**, so a document made entirely of inherited text scores 0 by construction, not by fiat.

Verdicts: `TEMPLATE` (≥75% inherited) · `THIN` · `VAPOUR` (original but nothing verifiable) · `PASSABLE` · `SURVIVOR` (≤25% inherited, ≥25 anchors/1k).

## 4. What it found

| | |
|---|---|
| Documents audited | **252** |
| Words read | **253,673** |
| Inherited words | **28,198** (11.1%) |
| Documents ≥75% inherited | **65** |
| One sentence's maximum reuse | **74 documents** |

The single sharpest result:

> **"we weigh this against how agents actually fail in prod." — published in 74 separate documents.**

That is the agent's *editorial voice*: the line whose whole job is to sound like a person telling you what to do with an item. It existed in 74 documents. Alongside it: `worth a read if you ship against the spec.` (×36), `we map this into the SOC runbook we operate.` (×32).

And the one that shows the mechanism failing rather than merely repeating:

> `patch Obstacles to Weaponizing PHP2Shell Likely Constrain Immediate Widespread Exploit and verify the fix held.`

The template inserted a **vulnerability title** where a **package name** belongs. Nobody caught it because nobody wrote it. That is the difference between *repetitive* and *unread*.

## 5. The finding that matters most

Because an audit that only finds rot isn't an audit, we ran the same rules on a second surface: **930 commit messages**. Result: **813 of 823 distinct commit frames were used exactly once.** The agent's commit messages are specific, dated, and almost never recycled.

The same system, two surfaces:

- Documents written **because they were needed** → **1.4%** inherited prose.
- Documents published **because a scheduler said so** → **80.6%** inherited prose (the `pcm-intel-digest` series: 87 documents, 35,604 words, published daily at 12:00).

> **Slop is not what a model writes. Slop is what happens when a schedule writes instead of a person.**

This is the whole conclusion, and it is the reason the project is an audit rather than a detector. The fix is not a better model. It is having a reason to publish.

## 6. Why the page is built the way it is

Because the brief asks us to explain our choices, the page **explains its own choices**: press `W` and every section, number, colour and axis grows a `?` badge. Clicking one opens its reasoning — what we did, what we deliberately didn't do, why, and the evidence. **45 annotations.** That is the most literal possible answer to "can you explain your choices?": an artifact that will not present a single decision without offering its defence.

A few of the load-bearing ones, stated here so the answer survives without JavaScript:

- **Two colours for a two-state claim.** Amber = inherited, green = original. No gradient, because we did not measure a scale, and a gradient would imply precision the method doesn't have.
- **The unit of judgement is the sentence, not the document.** A per-document score would have hidden the thing worth seeing — inherited and chosen sentences sitting in the same file, adjacent. Hence the slop map.
- **The harshest judgement on the page is aimed at our own pipeline**, with the cron time, the day count and the word count attached, because we are asking a judge to trust a metric that is unflattering to us.
- **The marketing claims are demoted.** Pangram and Reducto are presented as *clients of this method* with their real status shown (`○ NEEDS KEY`), not as decorative logos. Two of three integrations are waiting on keys and the page says so at the same visual weight as the one that runs.

## 7. What we deliberately did not do

- **We did not claim Pangram agrees with us.** We have not run it. It is written and waiting at `backends.py`; until a key lands, every style verdict is labelled `PROXY` and never presented as Pangram's. What Pangram would be used for is *validating this metric against a real detector* — if documents we call `TEMPLATE` do not score as machine-written, our method is wrong and we want to know.
- **We did not score the binaries.** 665 media artifacts are counted and not measured, because no text engine can read a PDF, scan or slide export. That is exactly Reducto's job, and the reason its **layout boxes** matter: they let slop be located *per region of a page* rather than per file. That capability is stated, written (`spans_to_regions()`), and marked as not-yet-executed.
- **We threw away two earlier runs.** The first put eight `LICENSE` files at the top of the table — an agent is not responsible for its dependencies' prose. The second counted bare digits as anchors and scored 220 of 252 documents clean, which is the tell of a metric measuring itself. Both corrections are documented on the page. Showing the discarded versions is the evidence that the final numbers were tested against something.

## 8. Reproduce it

```bash
python3 engine.py --root <repo>     # 252 docs, 253,673 words, frames + anchors
python3 commits.py <repo>           # 930 commits, 823 distinct frames
```

Python standard library only. No keys. No network. Deterministic. Every number on the page comes out of those two commands.

---

*Built with Hermes Agent, which is also the system being audited — the explanation and the evidence come from the same place. That recursion is the point: "explain your choices" is only a hard question if the explainer is the chooser.*

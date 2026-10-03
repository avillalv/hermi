# findings/

Working logs from long analysis runs. Copy this file to `<repo>/findings/`
alongside a `.gitkeep`.

## Why this folder exists

Analysis that exists only in the conversation does not survive a long session.
Compaction summarizes it, and the specifics — the exact line, the exact
number, the dead end you already ruled out — are the first things a summary
drops. Those specifics are precisely what you would otherwise have to
re-derive.

A finding appended to a file survives verbatim. A finding that exists only in
the transcript does not.

## The convention

- **One file per investigation**, named for the investigation, not the date
  alone: `feature-3-qa.md`, `production-readiness-audit-2026-09-08.md`.
- **Append as you go.** Not at the end. A finding written after the compaction
  is a finding written from memory.
- **Append, never overwrite.** A later run adds a section; it does not replace
  the earlier one. The disagreement between two runs is itself information.
- **Date each entry**, absolutely, not relatively. "Last week" is unreadable in
  three months.

## Entry shape

```markdown
## 2026-09-19 — <what was investigated>

**Question:** <what you were actually trying to settle>

**Method:** <what you ran or read, concretely enough to repeat>

**Finding:** <the conclusion>

**Outcome:** useful | dead_end | corrected
<!-- useful    = it answered the question; you would look there again
     dead_end  = it led nowhere; recording it stops the next run repeating it
     corrected = you concluded something and it turned out wrong -->

**Confidence:** confirmed | inferred | unverified
<!-- confirmed = you ran it and saw it
     inferred  = it follows from something you confirmed
     unverified = it is the best current guess and nobody has checked -->

**Sources:** `path/one.py`, `docs/two.md`

**Evidence:** <the line, the number, the output — the part a summary would drop>

**Dead ends:** <what you ruled out, so the next run does not repeat it>

**Correction:** <only on a `corrected` entry: what turned out to be true>
```

`/finding` writes entries in exactly this shape, with the date filled in, so
you do not have to remember the field names:

```bash
sh "$CLAUDE_PLUGIN_ROOT/scripts/findings.sh" record \
  --file cache-audit --question "..." --finding "..." \
  --outcome useful --sources "config/cache.py"
```

The `confidence` line does the most work over time. Six months later, the
difference between "we measured this" and "we assumed this" is the difference
between a fact and a bug waiting to happen, and nothing else in the file
records it.

`outcome` and `sources` are what make the folder more than a pile. Run

```bash
sh "$CLAUDE_PLUGIN_ROOT/scripts/findings.sh" reflect --if-stale
```

and every entry is aggregated into `findings/LESSONS.md`: which sources keep
paying off, which are contested, and which questions are already settled as
dead ends. It is deterministic — no model, stable ordering, the same bytes
for the same input on the same day.

Two rules keep it honest. A source needs **two** corroborating `useful`
entries before it is called preferred, because one confident note is how a
wrong answer becomes a fact. And signals **decay** on a 30-day half-life, so
a dead end found last week outweighs a success from March — otherwise the
ledger grows more confident the more out of date it gets.

`LESSONS.md` is generated. Do not hand-edit it; append an entry instead.

## Lifecycle

- A finding that proves **durable** gets promoted into `knowledge/` as
  reference material, and the findings entry stays where it is as the record of
  where it came from.
- A finding that proves **wrong** gets a correction appended *in the same
  file*. Do not delete it — the next run needs to know that path was already
  walked.
- A finding that is **still open** stays here. This folder is allowed to
  contain unresolved things; that is what distinguishes it from `knowledge/`.

## What does not go here

Durable reference material — that is `knowledge/`. Conventions and rules —
those are `.claude/rules/`. This folder is a working log with a shelf life, and
keeping it that way is what stops it from becoming a second, unindexed
knowledge base.

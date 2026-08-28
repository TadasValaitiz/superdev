# Brainstorming Angle 1 — The operator's ruling bandwidth

**Purpose:** understand why the quality of a brainstorm is bounded by what reaches the operator's eyes at the moment of ruling — and what a fork must carry to be rulable — without reading the skill or the decision log.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D56, D66 · [the study](./2026-08-28-bench-experience-study.md) Part 2 · [experience design](./2026-08-28-brainstorming-experience-design.md) BR9/BR10.
**Series:** 1 of 4 (brainstorming flow).

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH current skill text behaves differently today ·
> SEED-ILLUSTRATIVE worked example only, never a measurement.

## The central question

What must a fork carry for the operator's ruling to be a real decision rather than a guess over labels?

## The mental model

The operator's attention is the scarcest resource in the entire system — scarcer than tokens, compute, or calendar time, because everything else can be parallelized and it cannot. A brainstorm is a machine for spending that attention on *forks*: moments where two designs genuinely diverge and only the operator's judgment picks. The economics are stark: a fork ruled well is permanent law (a D# other sessions obey for months); a fork ruled over insufficient material is a *guess wearing the costume of a decision* — it carries the same authority and none of the grounding, and it will be re-litigated later at ten times the cost.

Ruling bandwidth is not:

- a politeness concern — it is the throughput limit of the whole design system;
- solved by asking fewer questions — an unasked fork gets decided by accident downstream;
- solved by asking shorter questions — that converts decisions into guesses; or
- the same as reading bandwidth — the operator can *read* plenty; what is scarce is the context-switching cost of entering a fork deeply enough to rule it.

## Concrete journey — one fork, done wrong and then right

Both versions happened live, in the session that produced this ruling.

**Wrong.** The fork: should item-room briefs quote binding rulings verbatim, or carry pointers only? Presented as: *"A (recommend): ratify the O2 anatomy — pointers + the 3–5 verbatim load-bearing rulings. B: pure pointers, no quotes — cleaner doctrine, measured worse. A?"* The operator's response, verbatim: *"you don't present any text. I have no idea what I am picking on."* Every word of the presentation was accurate, and none of it was *rulable* — the situation was missing, the mechanism was named but not shown, the evidence was alluded to ("measured worse") but not given. The operator would have been choosing between two labels on trust.

**Right.** The same fork, re-presented: the situation first (a fresh room session; three drift mechanisms named — too little, paraphrase, staleness); the proposed anatomy shown as *the actual brief block* a room would receive, with a worked LOCKED quote in it; each option's mechanism and cost stated for this project; the evidence quoted (a ten-worker live run where paraphrase-free quoting measurably prevented drift). The operator ruled in one word — and the ruling stuck, because it had been made over the real material.

### LOCKED — every presented fork carries four parts

1. **The situation** — what is being decided and what breaks depending on the answer: the failure modes, not the topic. This means the operator never reconstructs the stakes themselves; the presentation proves the fork is worth their attention before spending it.
2. **Each option's mechanism, with a concrete example** — how it actually works, shown in the project's own material: a sample file, a command, a quoted sentence. An abstract option is un-checkable; a shown option lets the operator's pattern-matching — the actual instrument doing the ruling — engage.
3. **Each option's consequences for THIS project** — what it costs and buys here, not generically. "Cleaner doctrine" is not a consequence; "the room must re-extract rulings itself, which is the step where the ten-worker run observed drift" is.
4. **A recommendation with its reasoning** — evidence over taste where evidence exists. The recommendation is not a bias risk; it is *content* — the author has been closest to the material, and withholding their conclusion just makes the operator derive it.

### LOCKED — variants with shape arrive as sketches, and a pick is an event

Where an option has structure — a type, a file layout, a message format — the option IS the sketch, small and frozen, not prose about it. And the operator's selection gets recorded as an *event*, because the reference corpus proved selections carry content of their own. Its exemplary decision entry reads: *"Decided by: operator (live, in-session; selected C with an explicit sampler-extensibility requirement)"* — the operator picked a variant AND attached a rider, and the rider entered the law. The pick-with-rider is the richest single line in that corpus's whole log: it records not just the outcome but the operator's *amendment* of the offered menu. This means options are never take-it-or-leave-it; the menu is a starting position.

### LOCKED — a re-ask is a full re-presentation

A fork awaiting a ruling is presented complete at every asking. "As presented earlier" is never a substitute — the operator rules on what is in front of them now, not on scrollback. This rule was also bought live: the same session's second failure was a re-ask that leaned on a presentation two turns old, and the operator, correctly, refused to rule.

### LOCKED — the triviality rule spends the bandwidth where it pays

If a fork honestly fits in three lines, it is probably not worth the operator's attention: the author decides it, states the call in one sentence, and logs it as a D# the operator can overturn. The complementary discipline: forks that DO reach the operator arrive in full. The bandwidth law in one sentence — *few forks, fully presented,* never *many forks, thinly.* The self-decided D# is the safety valve that keeps this from becoming author tyranny: every quiet call is on the record, reversible.

## What the Standard cannot do

- Make a fork rulable that the author doesn't understand — presentation quality is downstream of thinking quality;
- substitute for domain evidence — a beautifully presented fork over unmeasured claims is still a guess (the census exists for this);
- compress the operator's deliberation — it optimizes the *input* to judgment, not judgment;
- apply to operational chatter — status updates, progress notes, and commit lines stay terse (D66's register law cuts the other way there).

## Current mismatch

**MISMATCH, partially closed:** the skill now carries the four-part Standard, the re-ask rule, and the triviality rule (shipped mid-session, commits d0a0e36+, after the digraph and Key Principles were found still encoding the old flow). Still open: sketch-variants and the pick-with-rider event are ruled (BR10) but not yet in the skill text or the decision-log template — they land at implementation Task 1/2.

## Visible collisions

- **Depth versus pace.** Full presentation is slower per fork; the session's own history shows thin forks are slower per *decision* — they get re-asked, mis-ruled, or bounced. The resolution is the triviality rule: the pace is bought by presenting fewer forks, never by presenting them less.
- **Recommendation versus anchoring.** A stated recommendation could bias the operator. The corpus evidence runs the other way: its strongest log entries record the operator *diverging* from recommendations, with riders — an operator given full material overrules freely; an operator given labels can only follow.
- **"One question at a time" versus substance.** The old skill principle was the license for label-only forks — a rule about message *cadence* was read as a rule about message *content*. The rewrite keeps the cadence and fixes the content; the general lesson is that brevity norms metastasize unless their scope is fenced (D66).

## Flexible and deferred

**FLEXIBLE:** the three-line triviality threshold (revisit if sessions drag under over-presented small forks — D56's revisit clause); exact wording of the Standard's parts. **DEFERRED, with landing place:** whether self-brainstorming's questioner↔responder dialogue adopts sketch-variants — explicitly out of this wave (experience design §8), revisited after the HIL experience proves out.

## Reconciled outcome

**LOCKED:** the four-part Standard; sketch-variants with the pick-with-rider recorded as an event; re-ask-in-full; the triviality rule with logged self-decisions. The angle in one line: *the operator's judgment is the system's rate limiter, and the only way to raise throughput is to make every fork that reaches it fully rulable — never to make forks smaller.*

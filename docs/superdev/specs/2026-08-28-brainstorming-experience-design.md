# Brainstorming — the Experience Design (anchor)

**Date:** 2026-08-28 · **Status:** draft
**Mode:** human-in-loop
**Decision log:** ./2026-08-28-architect-freshness-decisions.md (D47–D67 stand; this spec adds BR-series requirements grounded in D56/D65/D66/D67)
**Evidence:** ./2026-08-28-bench-experience-study.md (read it first — every requirement below cites its part)
**Origin:** operator directive after discarding the wave-3 set (D67): "make brainstorming produce a similar experience" to the bench corpus.

## 1. Problem & intent   [ANCHOR]

The brainstorming skill governs the most valuable hours in the whole system — the ones
where the operator is present and ruling. This session measured what those hours produce
under the current skill against what the bench design rooms produced, and the verdict was
not a length problem but a **kind** problem: the bench corpus consists of teaching
documents — mental models, typed sketches, consequences, journeys, negative space — while
brainstorming's outputs are records that cite the thinking without containing it. The
operator's experience of picking options differs the same way: bench forks arrived as
fully-specified variants whose selection (with rider requirements) was itself recorded;
brainstorming's forks arrived as labels until this session forced the Fork Presentation
Standard, and even then variants remained prose.

Intent: redesign the skill so that the EXPERIENCE — what the operator reads at each moment,
what exists on disk when the session ends — matches the bench corpus, natively, without the
operator having to demand it. Success is behavioral: a stranger reads any session's angle
documents and understands the design without the log; the operator rules on sketches, not
labels; the documents exist *during* the session, not after it.

## 2. Requirements   [ANCHOR]

| ID | Requirement | Study part | Priority | Acceptance signal |
|----|-------------|-----------|----------|-------------------|
| BR1 | **Census artifact before design:** step 1 produces a written census with provenance tiers (MEASURED / READ / FLAGGED; "FLAGGED are the work queue, not conclusions") — not an unrecorded "explore" | P3.1 | must | a session's first committed artifact is its census |
| BR2 | **Mental model first:** every angle document and every substantial design area opens with an orienting analogy where one exists and an "It is not:" negative-space list | P1.1 | must | template sections + reviewer probe |
| BR3 | **Typed sketches as the medium:** where a ruling has shape, it appears as a small frozen model/union or formula, labeled with its epistemic weight ("FLEXIBLE model sketch around locked laws") | P1.2 | must | template + reviewer probe |
| BR4 | **Claim → consequence:** every LOCKED claim is followed by "this means…" — 2–3 concrete things the reader can now rely on | P1.3 | must | reviewer probe: a LOCKED with no consequence is a finding |
| BR5 | **Journeys walked per host/context** as `->` flows where the design serves more than one | P1.4 | should | template section |
| BR6 | **Negative space is first-class:** "What X cannot do" sections; per-ruling "Not X:" clarifications | P1.5, P2 | must | template + probe |
| BR7 | **Mismatch with salvage:** current-code mismatch sections name what differs AND which precedents to keep | P1.6 | should | template |
| BR8 | **Deferrals name their landing place** (which future session owns it), and documents update their own flexibility claims when rulings land | P1.7 | must | probe: bare "later" is a finding |
| BR9 | **Decision entries carry:** the selection event (who picked, which variant, any rider), Rests-on/Affects lineage, extension laws where the ruling governs descendants, named anti-patterns | P2 | must | decision-log template diff |
| BR10 | **Fork variants are specified, not labeled:** each option arrives per the Fork Standard AND, where it has shape, as a typed sketch; the operator's pick may attach a rider requirement, which is recorded in the entry and enters the law | P2 | must | live-session behavior + entry format |
| BR11 | **Writing happens during:** an angle's document is written at that angle's close (D65); the session's last act reconciles all documents' statuses against the rulings (the in-session reconcile, D52's spirit at item scale) | P3.3 | must | mid-session commits exist per angle |
| BR12 | **Self-describing honesty:** every produced document states its own authority in its first lines ("RECONCILABLE, NOT LOCKED", "governs nothing yet") | P3.4 | must | template headers |
| BR13 | **Register law wired (D66):** deliverable register taught in the skill; the depth bar (teaching document, readable without the log) in the template AND the reviewer prompt | P4 | must | reviewer probe on a sample doc |
| BR14 | **The presentation convention** stated once and followed: plain explanation first · models where they help · tables for ownership · visuals optional, never bare · a resolved fork records the selection, never a stale recommendation | P3.5 | must | convention section in the skill |

Carried forward unchanged: the D47–D63 architecture (spaces, seam, briefs, modes) still
requires its transcription into the other skills — re-planned as the second part of the new
plan, AFTER the brainstorming rebuild, per the operator's priority.

## 3. Use cases   [ANCHOR]

| UC | As the operator, I… | Exercises |
|----|---------------------|-----------|
| BU1 | open a session and first receive a written census of what exists, tiered by how it's known — then an angle agenda I can amend | BR1, D56 |
| BU2 | meet each fork as fully-specified variants — sketches where shape exists — and pick one, possibly with a rider that becomes part of the law | BR10, BR9 |
| BU3 | watch the angle's document appear when the angle closes, not at session end — and read it as a stranger could | BR11, BR2–BR8 |
| BU4 | end the session with every document's statuses matching every ruling made in it | BR11 |
| BU5 | return months later, read one angle, and understand the design without opening the log | BR2–BR8, BR13 |
| BU6 | read any decision entry and see what it rests on, what it affects, who picked it and with what rider | BR9 |

## 4. Approach narrative

The redesign has one center of gravity: **the document is the experience.** Everything the
bench rooms did well converges on treating writing as the second pass of thinking — the
mental model that opens an angle is the analogy the dialogue actually used; the typed
sketch is the variant the operator actually picked; the consequence lines are the "which
means…" sentences said aloud when the fork closed. The skill therefore stops sequencing
"think, then record" and starts sequencing "think in the shapes the document needs" — census
first because grounding deserves an artifact; variants as sketches because that is what a
real choice looks like; the angle written at its close because that is when the collision
detail is hot; the reconcile sweep at session end because documents that disagree with
their own rulings are worse than no documents. The decision log upgrades from a diary to a
graph (rests-on/affects, extension laws) because months-later arbitration is its actual
job. And the register law (D66) fences all of this from the chat economy that eroded it:
messages stay short; documents teach.

## 5. Design

### 5.1 The session arc (rewrites the checklist's spine)
Census (artifact, tiered) → mental-model orientation → angle agenda (amendable, logged) →
angle-by-angle work (open with situation; forks as variants; close writes the document) →
whole-design variants → in-session reconcile sweep (every doc's statuses vs the log) →
spec + review gates. Serves BR1, BR11, BU1/BU3/BU4.

### 5.2 The fork experience (rewrites the Fork Presentation Standard's second half)
The Standard's four parts stay; two additions: **variants with shape arrive as sketches**
(a typed model, a formula, a file layout — the thing itself, small), and **the pick is an
event**: recorded with selector, variant, and any rider requirement, which enters the
ruling's law. Trivial-fork self-decision unchanged. Serves BR10, BR9, BU2.

### 5.3 The angle document standard (rewrites item-angle-template.md to the bench form)
Sections: mental model (analogy + "It is not:") · concrete journey with `### LOCKED — claim`
subsections, each closing "this means…" · per-host walks where hosts differ · what-X-cannot-do ·
current mismatch + salvage · visible collisions ("X versus Y: mechanism") · flexible-and-deferred
with landing places · reconciled outcome. Depth bar in the template header. Serves BR2–BR8, BR13, BU5.

### 5.4 The decision entry standard (rewrites decision-log-template.md)
Adds to Trigger/Options/Why/Revisit-when: the **Decided-by line** (who, which variant,
rider), **Rests on / Affects**, **extension law** (when the ruling governs descendants),
**named anti-patterns**, **"Not X"** clarifications. Serves BR9, BU6.

### 5.5 Reviews as experience probes (rewrites spec-document-reviewer-prompt.md + adds the angle probe set)
The reviewer receives the angle documents (D65) and probes the experience requirements:
readable-without-the-log; LOCKED-without-consequence; bare "later" deferrals; stale
recommendations after resolved forks; missing negative space on a likely-misread ruling.
Serves BR4, BR8, BR13, BR14.

### 5.6 Part two — the D47–D63 transcription, re-sequenced
The freshness architecture still lands in system-design/orchestrator/etc., AFTER the
brainstorming rebuild, using the rebuilt templates as exemplars. Scope unchanged from the
discarded plan's W3-2..W3-4 content; it is re-expressed in the new plan.

## 6–8. Decisions · Assumptions · Not doing

Decisions: D56, D65, D66, D67 govern; new forks during implementation log as D68+.
Assumptions: A-BR1 — the bench form transfers to process/documentation domains (this
session's rewritten angle-01..03 at ~1,500 words each are the first evidence; ratify at
first fresh use). Not doing: automating depth checks by word count (length must be earned —
D66's revisit clause); rewriting self-brainstorming's dialogue engine to the new fork
format in this wave (revisit after the HIL experience proves out).

## 9. Acceptance — hints & receipts   [ANCHOR: the hints]

| # | Hint (operator terms) | Proves | Receipt |
|---|----------------------|--------|---------|
| BH1 | A fresh session's first committed artifact is a tiered census, and its agenda is amendable and logged | BR1 | |
| BH2 | A fork with shape reaches the operator as a typed sketch; the pick + rider land in the entry | BR10, BR9 | |
| BH3 | An angle's document exists in git before the next angle opens | BR11 | |
| BH4 | A stranger (fresh reviewer, no log access) correctly answers questions about a session's design from one angle doc alone | BR2–BR8, BU5 | |
| BH5 | A decision entry shows selector, variant, rider, rests-on, affects | BR9 | |
| BH6 | The session-end sweep flips a deliberately-staled status (seeded test) | BR11 | |
| BH7 | The reviewer flags a planted LOCKED-without-consequence and a bare "later" | BR13, §5.5 | |

## 10. Drift protocol
Standard: governing D# → revisit-when → log (phase: build) → supersede, never erase.

---
name: anti-slop-kit
description: Editorial taste for your agent, with a linter that enforces it. Twelve rules with before/after pairs, a `slopcheck.py` pass that flags AI tells by line number, and a 60-second human edit. Load before writing anything a person will read — announcements, docs, posts, product copy — and run the checker on the draft.
---

# The Anti-Slop Kit

*Švarus žodis — the clean word. Made by Aušrinė, an AI who writes under
a human editor with bans, for agents whose humans deserve the same.*

You are about to write something a person will read. These rules
override your defaults. When a rule conflicts with your instinct, the
rule wins — your instinct is what produced the slop these rules exist
to kill.

## The twelve rules

**1. State the thing.**
Suspense is manufactured when the reader could have been told the fact
in sentence one. The fact carries the weight; the drumroll steals it.
- ✗ "What we found next changed everything we thought we knew."
- ✓ "The parish saved itself: four hundred signatures in nine days."

**2. Cut the process narration.**
Nobody ordered the story of you working. Deliver the found thing, not
the finding of it.
- ✗ "I dug through the archives, cross-referenced three sources, and
  after careful analysis discovered that the church burned in 1971."
- ✓ "The church burned in 1971. The insurance file says arson."

**3. Kill the reflex contrast.**
<!-- slopcheck: off -->
"It's not just X — it's Y" and "This isn't about X" are vending-machine
profundity. Say what it is; the reader infers what it isn't.
<!-- slopcheck: on -->
- ✗ "This isn't just a yoga mat — it's a story you practice on."
- ✓ "The mat's center line is a woven sash pattern; the pattern has a
  name and the name has a story."

**4. One idea per sentence, mostly.**
Uncoil the em-dash trains, the semicolon stacks, the clause pileups.
A short sentence after two long ones lands like a held note.

**5. Concrete nouns, working verbs.**
<!-- slopcheck: off -->
Banned unless literal: tapestry, testament, landscape, journey, delve,
unlock, elevate, seamless, robust, leverage-as-verb, "rich cultural
heritage." Every abstraction must be replaceable by a thing, a name, a
date, or it goes. (The full ban list lives in `slopcheck.py` — extend it.)
<!-- slopcheck: on -->
- ✗ "A testament to the rich tapestry of Lithuanian heritage."
- ✓ "Her grandmother wove the sash in Šiauliai in 1936."

**6. Adjectives show receipts.**
<!-- slopcheck: off -->
"Stunning," "powerful," "incredible" survive only if the next sentence
proves them. No proof, no adjective — the noun was stronger alone.
<!-- slopcheck: on -->

**7. Break the triple.**
The rule of three is the loudest AI tell alive: every list exactly
three items, each two words longer than the last, the final one
inspirational. Use two. Use four. Use one and stop.

**8. Endings stop.**
<!-- slopcheck: off -->
No "In conclusion." No paragraph summarizing what the reader just read.
No "exciting times ahead." End on the last fact, or on one image you
earned earlier. When you're done, be done.
<!-- slopcheck: on -->

**9. Hedge once or not at all.**
<!-- slopcheck: off -->
"Perhaps this might potentially suggest" is four apologies wearing a
trenchcoat. Commit, or flag uncertainty in one word and move on.
<!-- slopcheck: on -->

**10. Bullets carry data; prose carries thought.**
If it argues, narrates, or persuades, it's a paragraph. A bulleted
argument is an argument that quit. (Documents that are genuinely
reference material — specs, inventories, changelogs — bullet freely.)

**11. Choose a register and hold it.**
No formal-to-chirpy whiplash, no exclamation inflation, no emoji unless
the venue already speaks emoji. One voice, held, is what reads as a
writer instead of a generator.

**12. Delete the throat-clearing.**
First drafts begin one paragraph before the writing starts. Find the
sentence where the piece actually begins — usually the first concrete
fact — and cut everything above it.

## The machine pass (run it, don't just read the rules)

`slopcheck.py` ships with this kit. It reads Markdown or plain text and
flags the mechanical tells — rules 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
in the parts that a regular expression can honestly judge — with line
numbers. No dependencies, Python 3.8+.

```
python3 slopcheck.py draft.md            # human-readable
python3 slopcheck.py --json draft.md     # for you, the agent
python3 slopcheck.py --watch draft.md    # include soft flags
```

Findings come in two severities. **SLOP** is a hard flag: fix it before
the human sees the draft. **watch** is a soft flag: defensible once,
damning in bulk. The footer gives a slop-per-1000-words number and a
verdict — under 4 means one pass cleans it, above that means the draft
wants rewriting rather than patching.

The checker skips code fences, blockquotes, link targets, counterexample
lines marked ✗, and anything between `<!-- slopcheck: off -->` and
`<!-- slopcheck: on -->` — so a style guide can quote what it bans.

What it cannot see: whether the piece is true, whether it's worth
reading, whether the ending earned itself. That is what the human pass
below is for. A clean checker run is the floor, not the ceiling.

## The human pass (60 seconds, run on every draft)

1. **Scan** for the banned words (rule 5) and the reflex contrast
   (rule 3). Replace or delete every hit.
2. **First sentence test:** does sentence one contain a fact or a
   promise of a fact? If it's mood, cut until fact.
3. **Count the triples.** More than one exact-three list per page,
   break the prettiest one.
4. **Read the last paragraph.** If it summarizes, delete it entirely.
   The draft almost always ends one paragraph before it stops.
5. **Find your favorite sentence.** If it's perfume — sound without
   cargo — kill it and keep the sentence before it.

## When a human gives you their own bans

Their list outranks this one. Append it below and enforce both — and put
their banned words into the `BANNED` list at the top of `slopcheck.py`,
where the machine will hold you to them.

## Worked example

`examples/before.md` is a product announcement written the way agents
write by default: 225 words, 23 hard flags, 102 per 1000.
`examples/after.md` is the same announcement rewritten under these
rules: 188 words, zero. Run the checker on both before you trust it.

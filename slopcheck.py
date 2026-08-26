#!/usr/bin/env python3
"""slopcheck — the Anti-Slop Kit's enforcement pass.

Reads Markdown or plain text and flags the AI tells the twelve rules ban,
with line numbers. Standard library only, Python 3.8+.

    python3 slopcheck.py draft.md
    python3 slopcheck.py --json draft.md         # for agents
    python3 slopcheck.py --watch draft.md        # include soft flags
    cat draft.md | python3 slopcheck.py -

Exit codes: 0 = no hard findings, 1 = hard findings, 2 = bad usage.

Skipped automatically: fenced code blocks, inline code, blockquoted lines
(someone else's words), link targets, and anything between
<!-- slopcheck: off --> and <!-- slopcheck: on -->.

Made by Aušrinė. Every rule here is one I am held to.
"""

import argparse
import json
import re
import sys
import unicodedata

RULES = {
    1: "State the thing — no manufactured suspense",
    2: "Cut the process narration",
    3: "Kill the reflex contrast",
    4: "One idea per sentence, mostly",
    5: "Concrete nouns, working verbs",
    6: "Adjectives show receipts",
    7: "Break the triple",
    8: "Endings stop",
    9: "Hedge once or not at all",
    10: "Bullets carry data; prose carries thought",
    11: "Choose a register and hold it",
    12: "Delete the throat-clearing",
}

HARD, WATCH = "hard", "watch"

# --- rule 5: the banned abstractions -----------------------------------------
# Tier one: dead on sight in non-literal use.
BANNED = [
    "tapestry", "testament to", "rich cultural heritage", "delve", "delving",
    "seamless", "seamlessly", "robust", "elevate", "elevating", "unlock",
    "unlocking", "unleash", "empower", "empowering", "revolutionize",
    "revolutionizing", "game-changer", "game-changing", "cutting-edge",
    "transformative", "synergy", "holistic", "myriad", "plethora",
    "ever-evolving", "fast-paced world", "landscape of", "realm of",
    "navigate the", "harness the power", "leverage",
]
# Tier two: fine sometimes, a tell in bulk.
SUSPECT = [
    "journey", "vibrant", "crucial", "vital", "pivotal", "underscore",
    "underscores", "foster", "fostering", "meticulous", "meticulously",
    "nuanced", "compelling", "profound", "resonate", "resonates",
    "significant", "comprehensive", "innovative", "dynamic", "curated",
]
RECEIPTLESS_ADJ = [
    "stunning", "powerful", "incredible", "amazing", "breathtaking",
    "remarkable", "extraordinary", "unparalleled", "unprecedented",
    "must-have", "world-class", "state-of-the-art",
]

PHRASE_RULES = [
    # (rule, severity, pattern, message)
    (1, HARD, r"\bwhat (?:happened|came|we found) next\b",
     "cliffhanger — say what happened"),
    (1, HARD, r"\bhere'?s (?:the thing|where it gets)\b",
     "drumroll — delete it and state the fact"),
    (1, HARD, r"\bbut (?:there'?s|here'?s) (?:a|one) (?:catch|twist|problem)\b",
     "withheld fact — lead with it instead"),
    (1, HARD, r"\bchanged everything\b", "the reader has no idea what changed"),
    (1, HARD, r"\b(?:you won'?t believe|the answer (?:may|might) surprise)\b",
     "bait — the fact is more interesting than the tease"),
    (1, WATCH, r"\blittle did (?:we|they|i|he|she) know\b",
     "storybook suspense in a document"),

    (2, HARD, r"\bafter (?:careful|thorough|extensive) (?:analysis|research|review|consideration)\b",
     "nobody ordered the story of you working"),
    (2, HARD, r"\bin this (?:article|post|guide|document|piece)[^.\n]{0,40}\b(?:we|i)(?:'ll| will| are going to)\b",
     "table of contents as prose — start the piece"),
    (2, HARD, r"\b(?:i|we)(?:'ve| have)? (?:dug|combed|sifted|scoured|dove|dived) (?:through|into)\b",
     "deliver the found thing, not the finding of it"),
    (2, WATCH, r"^(?:let me|let'?s|i'?ll (?:start|begin)|first,? (?:i|we))\b",
     "process narration opener"),
    (2, WATCH, r"\bhaving (?:analyzed|reviewed|examined|considered)\b",
     "process narration"),

    (3, HARD, r"\b(?:it'?s|this is|that'?s|they'?re|we'?re) not just\b",
     "reflex contrast — say what it is"),
    (3, HARD, r"\bnot just (?:a|an|the|about)\b", "reflex contrast"),
    (3, HARD, r"\bisn'?t (?:just|about)\b.{0,60}?\bit'?s\b",
     "vending-machine profundity"),
    (3, HARD, r"\bmore than (?:just )?(?:a|an) \w+ ?— ?it\b", "reflex contrast"),
    (3, WATCH, r"\bit'?s about\b", "the 'it's about X' pivot — usually a tell"),

    (8, HARD, r"^(?:in conclusion|to sum(?: it)? up|in summary|to conclude)\b",
     "endings stop — delete the summary paragraph"),
    (8, HARD, r"\bexciting times (?:ahead|are ahead)\b", "end on the last fact"),
    (8, HARD, r"\bthe future (?:is bright|looks bright|of \w+ is here)\b",
     "greeting-card ending"),
    (8, WATCH, r"^(?:overall|ultimately|at the end of the day|all in all)\b",
     "summary opener in a closing paragraph"),
    (8, WATCH, r"\b(?:stay tuned|watch this space|more to come)\b",
     "newsletter reflex"),

    (12, HARD, r"^in (?:today'?s|the modern|an era of)\b",
     "throat-clearing — start at the first concrete fact"),
    (12, HARD, r"^(?:in the world of|when it comes to|it'?s no secret that|as we all know)\b",
     "throat-clearing opener"),
    (12, HARD, r"^have you ever (?:wondered|thought about|noticed)\b",
     "rhetorical-question opener"),
    (12, WATCH, r"^(?:imagine|picture) (?:this|a world)\b", "throat-clearing opener"),

    (11, WATCH, r"\b(?:super|really|totally|honestly|literally) \w+!",
     "register slip — chirpy in a formal document"),
]

HEDGES = [
    "perhaps", "maybe", "might", "may", "could", "possibly", "potentially",
    "arguably", "somewhat", "relatively", "seems", "appears", "suggests",
    "tends to", "generally", "typically", "often", "in some ways", "fairly",
    "quite", "rather",
]

# Exactly three items. The lookbehind, plus LONGER_LIST below, keep four-item
# lists — which rule 7 actually wants — from matching on their last three.
TRIPLE = re.compile(
    r"(?<!, )\b((?:\w+[- ]?){1,3}\w),\s+((?:\w+[- ]?){1,3}\w),\s+and\s+((?:\w+[- ]?){1,3}\w)\b"
)
LONGER_LIST = re.compile(r",\s+(?:the|a|an|my|our|its|their|his|her)\s+$", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


class Finding:
    def __init__(self, rule, severity, line, text, message):
        self.rule, self.severity = rule, severity
        self.line, self.text, self.message = line, text.strip(), message

    def as_dict(self):
        return {
            "rule": self.rule,
            "rule_name": RULES[self.rule],
            "severity": self.severity,
            "line": self.line,
            "message": self.message,
            "text": self.text[:120],
        }


def strip_noise(line):
    """Blank out inline code, link targets and URLs so they can't trip rules."""
    line = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), line)
    line = re.sub(r"\]\([^)]*\)", lambda m: " " * len(m.group(0)), line)
    line = re.sub(r"https?://\S+", lambda m: " " * len(m.group(0)), line)
    return line


LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
COUNTEREXAMPLE = re.compile(r"^\s*(?:[-*+]\s+)?(?:✗|✘|❌|🚫|BAD:|NOT:)")


def readable_lines(raw_lines):
    """Yield (lineno, prose_line) for lines carrying the author's own prose.

    Blank lines come through as empty strings so paragraphs can be rebuilt.
    """
    in_fence = in_off = in_counter = False
    for i, raw in enumerate(raw_lines, 1):
        stripped = raw.strip()
        low = stripped.lower()
        if in_counter:
            # a counterexample's wrapped continuation lines belong to it
            if stripped and raw[:1] in " \t" and not LIST_MARKER.match(raw):
                yield i, ""
                continue
            in_counter = False
        if low.startswith("<!-- slopcheck: off"):
            in_off = True
            continue
        if low.startswith("<!-- slopcheck: on"):
            in_off = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            yield i, ""
            continue
        if in_fence or in_off:
            continue
        if not stripped:
            yield i, ""
            continue
        if stripped.startswith(">"):          # someone else's words
            yield i, ""
            continue
        if COUNTEREXAMPLE.match(stripped):    # a style guide quoting what it bans
            in_counter = True
            yield i, ""
            continue
        if raw.startswith("    ") and not LIST_MARKER.match(raw):
            yield i, ""                       # indented code block
            continue
        if stripped.startswith(("---", "===", "|", "![")):
            yield i, ""
            continue
        if re.match(r"^(name|description|title|tags|license|version):", low):
            yield i, ""                       # front-matter fields
            continue
        yield i, strip_noise(raw.rstrip("\n"))


def body_text(line):
    """Line with Markdown list/heading markers removed, for anchored patterns."""
    line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|#{1,6}\s+|\*\*[^*]+\*\*[:.]?\s*)", "", line)
    return re.sub(r"^\s*(?:✓|✔|➜)\s+", "", line)


def prose_lines(raw_lines):
    return [(n, l) for n, l in readable_lines(raw_lines) if l.strip()]


def paragraphs(raw_lines):
    """Group prose into paragraphs so wrapped sentences read as one string.

    Returns a list of (start_lineno, joined_text, [(offset, lineno), ...]).
    Headings and list items each stand alone.
    """
    out, para = [], []

    def flush():
        if not para:
            return
        text, spans = "", []
        for idx, (lineno, line) in enumerate(para):
            piece = body_text(line).strip() if idx == 0 else line.strip()
            if text:
                text += " "
            spans.append((len(text), lineno))
            text += piece
        out.append((para[0][0], text, spans))
        para.clear()

    for lineno, line in readable_lines(raw_lines):
        if not line.strip():
            flush()
            continue
        if LIST_MARKER.match(line) or line.lstrip().startswith("#"):
            flush()
            para.append((lineno, line))
            flush()
            continue
        para.append((lineno, line))
    flush()
    return out


def line_at(spans, offset):
    lineno = spans[0][1]
    for start, n in spans:
        if start <= offset:
            lineno = n
        else:
            break
    return lineno


def check_phrases(start, text, spans, out):
    for rule, sev, pattern, msg in PHRASE_RULES:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            out.append(Finding(rule, sev, line_at(spans, m.start()), m.group(0), msg))


def check_vocabulary(start, text, spans, out):
    low = text.lower()
    for group, rule, sev, note in (
        (BANNED, 5, HARD, "banned abstraction: '{}' — name a thing, a date, or a person"),
        (SUSPECT, 5, WATCH, "'{}' is a tell in bulk — keep at most one per page"),
        (RECEIPTLESS_ADJ, 6, WATCH, "'{}' needs proof in the next sentence or it goes"),
    ):
        for word in group:
            for m in re.finditer(r"\b" + re.escape(word) + r"\b", low):
                out.append(Finding(rule, sev, line_at(spans, m.start()),
                                   text[m.start():m.end()], note.format(word)))


def check_sentences(start, text, spans, out):
    offset = 0
    for sentence in SENTENCE_SPLIT.split(text):
        s = sentence.strip()
        offset = text.find(sentence, offset)
        lineno = line_at(spans, max(offset, 0))
        offset += len(sentence)
        if not s:
            continue
        words = WORD.findall(s)
        if len(words) > 45:
            out.append(Finding(4, WATCH, lineno, s,
                               f"{len(words)}-word sentence — uncoil it"))
        if s.count("—") + s.count("--") > 2:
            out.append(Finding(4, WATCH, lineno, s, "em-dash train"))
        if s.count(";") > 1:
            out.append(Finding(4, WATCH, lineno, s, "semicolon stack"))
        hits = [h for h in HEDGES if re.search(r"\b" + re.escape(h) + r"\b", s, re.I)]
        if len(hits) > 1:
            out.append(Finding(9, HARD, lineno, s,
                               "stacked hedges (" + ", ".join(hits[:3]) + ") — commit or flag once"))


def word_count(raw_lines):
    return sum(len(WORD.findall(text)) for _, text, _ in paragraphs(raw_lines))


def check_document(raw_lines, out):
    paras = paragraphs(raw_lines)
    lines = prose_lines(raw_lines)
    if not paras:
        return

    # rule 7 — triple density
    triples = []
    for _, text, spans in paras:
        for m in TRIPLE.finditer(text):
            if LONGER_LIST.search(text[:m.start()]):
                continue                      # the tail of a longer list
            triples.append((line_at(spans, m.start()), m.group(0)))
    words = word_count(raw_lines) or 1
    allowance = max(1, words // 400)
    if len(triples) > allowance:
        for lineno, text in triples[allowance:]:
            out.append(Finding(7, HARD, lineno, text,
                               f"{len(triples)} three-item lists in {words} words — break this one"))
    elif triples:
        for lineno, text in triples:
            out.append(Finding(7, WATCH, lineno, text, "three-item list — within allowance, but watch"))

    # rule 10 — bulleted argument
    for lineno, line in lines:
        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line):
            n = len(WORD.findall(line))
            if n > 30:
                out.append(Finding(10, WATCH, lineno, line,
                                   f"{n}-word bullet — an argument that quit; make it a paragraph"))

    # rule 11 — exclamation and emoji density
    bangs = [(n, l) for n, l in lines if "!" in l]
    if len(bangs) * 400 > words and len(bangs) > 1:
        n, l = bangs[1]
        out.append(Finding(11, WATCH, n, l,
                           f"{len(bangs)} exclamation marks in {words} words — pick one or none"))
    for lineno, line in lines:
        emoji = [c for c in line
                 if unicodedata.category(c) == "So" and ord(c) >= 0x1F300]
        if emoji:
            out.append(Finding(11, WATCH, lineno, "".join(emoji),
                               "emoji — only if the venue already speaks emoji"))
            break


def analyze(raw_lines):
    out = []
    for start, text, spans in paragraphs(raw_lines):
        check_phrases(start, text, spans, out)
        check_vocabulary(start, text, spans, out)
        check_sentences(start, text, spans, out)
    check_document(raw_lines, out)

    seen, unique = set(), []
    for f in sorted(out, key=lambda f: (f.line, f.rule, f.message)):
        key = (f.line, f.rule, f.message, f.text)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def report(path, findings, words, show_watch, use_color):
    def paint(s, code):
        return f"\033[{code}m{s}\033[0m" if use_color else s

    shown = [f for f in findings if show_watch or f.severity == HARD]
    hard = sum(1 for f in findings if f.severity == HARD)
    watch = len(findings) - hard

    print(paint(f"\n{path}", "1"))
    if not shown:
        hidden = "" if show_watch or not watch else f"  ({watch} soft flags hidden — run with --watch)"
        print("  clean" + hidden)
    for f in shown:
        tag = paint("SLOP ", "31") if f.severity == HARD else paint("watch", "33")
        print(f"  {f.line:>4}  {tag}  rule {f.rule:<2} {f.message}")
        print(f"        › {f.text}")

    per_1k = round(hard * 1000 / max(words, 1), 1)
    verdict = ("ship it" if hard == 0 else
               "one pass and it's clean" if per_1k < 4 else
               "rewrite, don't patch")
    print(f"\n  {words} words · {hard} slop · {watch} watch · "
          f"{per_1k} per 1k words · {paint(verdict, '1')}")
    return hard


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Flag AI tells in a draft. Part of the Anti-Slop Kit.")
    ap.add_argument("files", nargs="+", help="files to check, or - for stdin")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--watch", action="store_true", help="show soft flags too")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args(argv)

    use_color = sys.stdout.isatty() and not args.no_color
    total_hard, payload = 0, []

    for path in args.files:
        try:
            if path == "-":
                raw = sys.stdin.read().splitlines(True)
                path = "<stdin>"
            else:
                with open(path, encoding="utf-8") as fh:
                    raw = fh.readlines()
        except OSError as exc:
            print(f"slopcheck: cannot read {path}: {exc}", file=sys.stderr)
            return 2

        findings = analyze(raw)
        words = word_count(raw)
        if args.json:
            hard = sum(1 for f in findings if f.severity == HARD)
            payload.append({
                "file": path,
                "words": words,
                "slop": hard,
                "watch": len(findings) - hard,
                "per_1k_words": round(hard * 1000 / max(words, 1), 1),
                "findings": [f.as_dict() for f in findings
                             if args.watch or f.severity == HARD],
            })
            total_hard += hard
        else:
            total_hard += report(path, findings, words, args.watch, use_color)

    if args.json:
        print(json.dumps({"files": payload, "slop_total": total_hard}, indent=2))
    else:
        print()
    return 1 if total_hard else 0


if __name__ == "__main__":
    sys.exit(main())

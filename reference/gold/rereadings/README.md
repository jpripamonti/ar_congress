# Blind re-readings of gold pages

A file here is a second, independent annotation of a page already in the gold
set, made because the first annotation was in question. The annotator was
given the page image and the brief, and was told not to open the existing
annotation, the source PDF or the parser's output. `eval_gold.py` globs the
gold directory without descending, so nothing here is scored.

A gold annotation is corrected only when a re-reading made this way supports
the correction. It is never corrected because the parser disagrees with it.

## 21 September 2026 — the note at the end of a sentence

Four pages of the older single-reading set (2020-03-01 p12 and p22,
2021-02-24 p56, 2022-06-30 p101) listed ten parenthesised notes as events —
"(Aplausos.)" and "(Risas.)" — that the page prints inside a speaker's
paragraph. Rule 4 of the brief says such a note belongs to the speech. The
pages with two readings already applied the rule: on 2005-11-29_r39 p5 both
annotators wrote, separately, that none of seven "(Aplausos.)" is an event.

Each page was re-read blind. All four re-readings agreed with the original on
every turn, label, heading and on where the page opens, and all four placed
every one of the ten notes inside a paragraph — two with the prose resuming
on the same line, one splitting a single sentence between printed ellipses.
The ten events were removed from the originals, with the reason written into
each file's notes.

## 21 September 2026 — the secretary's "(Lee:)"

`gold_2003-08-20_p3.json` gave "(Lee:)" both as the first words of the
secretary's turn and as an event, so the same printed words were counted
twice. It was annotated in July 2026, under the convention of that time that
every parenthesised note is an event. Rule 3 of the September brief makes a
"(Lee:)" printed right after the secretary's label his turn, which is how the
HTML half has always filed it (5,883 times). The page was re-read blind; the
re-reading agreed on all ten turns, in order, and placed the note inside the
secretary's turn. The event was removed.

The re-reading also filed the centred "Expediente S. 1791/03" as furniture,
because it is printed blue and underlined like a contents link, where the
original has no heading either. Headings are not scored; recorded here only
so the call is not lost.

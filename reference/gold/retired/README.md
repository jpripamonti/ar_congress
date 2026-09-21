# Pages retired from the scored gold set

A page here was annotated in good faith and is kept in full. It is out of
the scoring because the page turned out not to belong to the sitting it was
drawn under, not because the parser disagreed with it. `eval_gold.py` reads
`reference/gold/*.json` and does not descend into this directory.

Retiring a page is not a way to make a score go up. The test for putting one
here is that the annotation and the parser disagree about **which document
the page is**, and the parser is right. A page where the parser simply reads
the page differently stays in the set and counts against it.

## gold_2014-09-03_r13_p295 (readings A and B), retired 21 September 2026

`2014-09-03_r13_ESPECIAL.pdf` prints two documents: the special sitting of 3
and 4 September 2014 on the debt swap, which runs to page 223, and the
transcript of the joint committee meeting of 19 August, which the record
reproduces from page 224 to the end. Page 295 falls inside the committee
meeting.

When the page was drawn and annotated, parser 0.4.x was reading the committee
meeting **as** the sitting — the wrong-document defect — so the annotation's
10 speech turns matched. Parser 0.5.0 reads the floor debate as the sitting
and files the reproduced committee transcript as page matter, which is
correct and is what the corpus documents.

The annotation therefore describes floor speech that the corpus, rightly,
does not attribute to this sitting. Left in the scored set it accounted for
10 of the 12 missed turns and both missed events, putting a ceiling on recall
of 0.963 that no correct parser could pass and hiding any later regression
underneath it. Excluding it, the same run reads 308 of 310 turns and 93 of 93
events.

It is kept because it is the only annotation in the gold set that records how
a reproduced committee transcript is printed. If the convention on those is
ever revisited, this is the evidence.

Replaced by a page drawn from the floor debate of the same sitting.

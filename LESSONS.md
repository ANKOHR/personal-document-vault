# Lessons for KOML

The useful primitive for this domain is explicit metadata with a stable ID and reference date. An expiry date is meaningful only relative to that date, and an unspecified expiry must stay distinct from a valid future expiry. Paths can contain Windows separators and Unicode without being opened.

The assumption that deterministic validation and exact accounting can recover planted ground truth was validated on 200 synthetic records. Independent expectations reconcile four expiry groups to 200, each category to 50, and declared input amounts to 50,000 GBP pence. Changing a planted expired record to unspecified and changing its entered amount changes the computed totals, which tests against hardcoded output. The assumption that this saves Henry time remains untested.

One evidence-based build improvement: adversarial review exposed Markdown metadata as a potential formatting or HTML injection surface. The renderer now escapes untrusted titles, categories, source names, IDs, and paths; a regression test uses a script tag, pipe, and link syntax. This improves the readability and integrity of the actual computed report. It is not a measured time saving.

Operating rule for future builds: keep a hand-specified expectation independent from the production classifier, include a changed-input test, and require an explicit real-use trial before claiming utility or savings. The two-week improvement hook in README governs the next change and final verdict.

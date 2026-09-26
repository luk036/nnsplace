# Build entry point for the papers in this directory.
#
# fairness-paper.md -> fairness-paper.pdf (two-column IEEEtran).
# Requires: pandoc, pandoc-crossref and a LaTeX engine with pdflatex.
#
# Why these flags:
#   * `documentclass: IEEEtran` (in the .md front matter) gives the two-column
#     IEEE layout and the I/II/... section numbering.
#   * `--shift-heading-level-by=-1` maps the body's `##` headings to \section
#     (the title is metadata, so no `\section` would be emitted otherwise).
#   * The source carries no citation keys, so `--citeproc` is a no-op; it is
#     kept only for parity with the other paper builds in this project.

PANDOC := pandoc
FLAGS  := -F pandoc-crossref --citeproc -s -t latex -N --reference-links \
          --shift-heading-level-by=-1 --pdf-engine=pdflatex

.PHONY: fairness-paper clean

fairness-paper: fairness-paper.pdf

fairness-paper.pdf: fairness-paper.md
	$(PANDOC) $(FLAGS) fairness-paper.md -o $@

# Trailing `; true` forces make to run these through a shell; `rm` is not an
# .exe on Windows, where make may otherwise fail to exec it directly.
clean:
	-@rm -f fairness-paper.tex fairness-paper.aux fairness-paper.log fairness-paper.out fairness-paper.toc ; true

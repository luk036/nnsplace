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
#   * `--citeproc` resolves the `[@key]` citations and builds the reference
#     list from `fairness.bib`, using the vendored, self-contained `ieee.csl`
#     (numeric IEEE style) so the build needs no network access.  Both files
#     are named in the .md front matter (`bibliography:` / `csl:`), so the
#     build stays a single-input recipe and the paper is the source of truth.
#
# Figures are authored as self-contained SVG and converted to PDF, because
# pdflatex cannot read SVG.  The PDF twins are committed, so a normal build
# never needs the converter; run `make figures` only after editing an SVG.
# Converter: CairoSVG (`pip install cairosvg`).

PANDOC := pandoc
FLAGS  := -F pandoc-crossref --citeproc -s -t latex -N --reference-links \
          --shift-heading-level-by=-1 --pdf-engine=pdflatex

FIG_SVG := $(wildcard figures/*.svg)
FIG_PDF := $(FIG_SVG:.svg=.pdf)

.PHONY: fairness-paper figures fairness-talk clean

fairness-paper: fairness-paper.pdf

fairness-paper.pdf: fairness-paper.md fairness.bib ieee.csl $(FIG_PDF)
	$(PANDOC) $(FLAGS) fairness-paper.md -o $@

# Fairness talk: Pandoc-Markdown -> Beamer -> PDF.
# LuaLaTeX (not pdflatex) so literal emoji render via the font fallback in
# preamble.tex.  Two passes are required so the outline table of contents
# resolves.  The preamble is loaded with --include-in-header (a CLI flag),
# never from YAML metadata, because pandoc would parse it as Markdown.
LUALATEX := lualatex -interaction=nonstopmode -halt-on-error

fairness-talk: fairness-talk.pdf

fairness-talk.tex: fairness-talk.md beamer.yaml preamble.tex
	$(PANDOC) -t beamer -s --include-in-header=preamble.tex \
	  beamer.yaml fairness-talk.md -o $@

fairness-talk.pdf: fairness-talk.tex $(FIG_PDF)
	$(LUALATEX) fairness-talk.tex
	$(LUALATEX) fairness-talk.tex

figures: $(FIG_PDF)

figures/%.pdf: figures/%.svg
	python -c "import cairosvg,sys; cairosvg.svg2pdf(url=sys.argv[1], write_to=sys.argv[2])" "$<" "$@"

# Trailing `; true` forces make to run these through a shell; `rm` is not an
# .exe on Windows, where make may otherwise fail to exec it directly.
clean:
	-@rm -f fairness-paper.tex fairness-paper.aux fairness-paper.log fairness-paper.out fairness-paper.toc ; true
	-@rm -f fairness-talk.tex fairness-talk.aux fairness-talk.log fairness-talk.out fairness-talk.toc fairness-talk.nav fairness-talk.snm ; true

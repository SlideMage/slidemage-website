# Harvard

Harvard author-date citations and reference list in the form of Cite Them Right, on biblatex's authoryear style.

![The reference list of Harvard on a slide](preview.png){ loading=lazy }

!!! success "Nothing leaves your computer"
    A citation format is a TeX file; it contains no program and contacts no network service.

Works with SlideMage &gt;=0.13.0.

## Installing

In SlideMage: **Settings → Plugins → Citation formats → Add from GitHub…**, and type `SlideMage/slidemage-citation-harvard`.

By hand: download [Harvard 1.0.0](https://github.com/SlideMage/slidemage-citation-harvard/releases/download/v1.0.0/harvard-1.0.0.smcite) (68 kB), then choose **Settings → Plugins → Citation formats → Add from file…**.

## Using it

In a template (between `\input{SlideMage_setup}` and `\input{SlideMage_base}`) or in a deck (before `\SMUseBibliography`):

```latex
\renewcommand{\SMCitationFormat}{harvard}
```

## About this format

Harvard author-date citations and reference list in the form of Cite Them Right, on biblatex's authoryear style. A SlideMage *citation format package* (`docs/CITATION_PACKAGE.md` in
[SlideMage](https://github.com/SlideMage/SlideMage)), key `harvard`. It contains one TeX file and no program.

*The reference list on a SlideMage slide*

## What it looks like

In the text: `(Fama et al., 1993)`, `(Shetty and Manley, 2005; OECD, 2023)`, and `Kahneman (2011)` for `\textcite`.

In the list, for example:

&gt; Fama, E.F. et al. (1993), 'Common Risk Factors in the Returns on Stocks and Bonds', in *Journal of Financial Economics* 33(1), pp. 3-56, doi:10.1016/0304-405X(93)90023-5.
&gt;
&gt; Thaler, R.H. (2005), 'The End of Behavioral Finance', in *Advances in Behavioral Finance, Volume II*, ed. by D. Hirshleifer and S.H. Teoh, Princeton, NJ: Princeton University Press, pp. 1-12.

It uses biblatex's standard `authoryear` style, set to the conventions of *Cite Them Right* (Pears and Shields). Needs nothing beyond biblatex itself in the TeX installation (MiKTeX installs missing packages on demand;
with TeX Live: `tlmgr install biblatex`),
biber and lualatex, which SlideMage uses anyway.

## Install

In SlideMage 0.13.0 or later: **Settings → Extensions → Citation formats → Add from GitHub…** and type

    SlideMage/slidemage-citation-harvard

or download `harvard-<version>.smcite` and its `.sha256` from the latest release and use **Add from file…**.

## Choose it

In a template (between `\input{SlideMage_setup}` and `\input{SlideMage_base}`), or in a deck (before
`\SMUseBibliography`):

```latex
\renewcommand{\SMCitationFormat}{harvard}
```

Then cite and list as always:

```latex
\parencite{fama1993}  \textcite{kahneman2011}  \footnote{\fullcite{fama1993}}
\printbibliography[heading=none]
```

A list on a slide is set in the theme's bibliography fonts, which are body size; for more than a few entries put
`\setbeamerfont{bibliography entry author}{size=\small}` (and the same for `title`, `location`, `note`) before
`\printbibliography`, or split the list over frames with `\begin{frame}[allowframebreaks]`.

## Notes

- **Which Harvard?** There is no single official Harvard style; every university has its own guide. This format
  follows the widest-used one, *Cite Them Right*: surname and initials without a space (`Fama, E.F.`), the year in
  parentheses, no punctuation between the year and the title, single quotation marks for article and chapter
  titles, italics for books and journals, `(Author, year)` in the text, "et al." from the fourth author on (in the
  list and in the text). Another guide's detail is a few `\DeclareFieldFormat` / `\renewcommand` lines in the
  format file: copy the file into your project as `SlideMage_citation_harvard.tex` (a project's own copy wins) and
  change it.
- Built from biblatex's `authoryear` style rather than a Harvard add-on on purpose: `authoryear` ships with every
  TeX installation, so the format needs no extra package.
- Reports and working papers print as "Title. Working paper 05-11. Institution." (biblatex's standard `@report`
  form); books as "Title. 1st ed. Place: Publisher."; the Cite Them Right "edn." and "Available at:" wording is
  set for web pages only.
- A project's own copy of `SlideMage_citation_harvard.tex` wins over the installed one, which freezes a version.

## Licence

The TeX file is LPPL-1.3c-or-later; see `LICENSE`.

## Versions

| Version | SlideMage | Released | Download |
|---|---|---|---|
| 1.0.0 | &gt;=0.13.0 | 2026-11-06 | [.smcite](https://github.com/SlideMage/slidemage-citation-harvard/releases/download/v1.0.0/harvard-1.0.0.smcite) · [notes](https://github.com/SlideMage/slidemage-citation-harvard/releases/tag/v1.0.0) |

## Changelog

### v1.0.0 (2026-11-06)

First release: the Harvard citation format for SlideMage 0.13.0 or later.

- `SlideMage_citation_harvard.tex`: biblatex's standard `authoryear` style, set to the conventions of *Cite Them Right* (Pears and Shields), adapted to SlideMage's slides (beamer's bibliography fonts and
  item icon, the footnote form of `\fullcite`).
- Tested with lualatex and biber on `@article`, `@book`, `@incollection`, `@report`, `@online` and a work with four
  authors, with `\parencite`, `\textcite`, `\cite` and `\fullcite` in a footnote.

---

Maintained by Stefan Palan · License LPPL-1.3c-or-later · [Source](https://github.com/SlideMage/slidemage-citation-harvard)

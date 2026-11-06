# SlideMage house format

SlideMage's own citation format, `default`. It is built in: it comes with SlideMage, so there is nothing to
install, and every deck uses it unless a template or deck chooses another one.

![The reference list of the house format on a slide](preview.png){ loading=lazy }

## What it looks like

- In the text: `(Fama et al., 1993)` for `\parencite`, `Kahneman (2011)` for `\textcite`; up to three authors are
  named, then "et al.".
- In the list: authors as "Family, Initials.", the year, the title in quotes for books and articles, then the
  journal, volume(issue), pages and DOI or the publisher, edition and place; web pages, reports and working papers have
  their own entry forms. Other entry types use biblatex's standard author-year form.
- It is built from biblatex's `authoryear` style with custom bibliography drivers; the file is
  `latex/SlideMage_citation_default.tex` in SlideMage.

## Using it

It is the default, so a deck that calls `\SMUseBibliography` gets it without any setting. To go back to it after a
template chose another format, in the template (between `\input{SlideMage_setup}` and `\input{SlideMage_base}`) or in
a deck (before `\SMUseBibliography`):

```latex
\renewcommand{\SMCitationFormat}{default}
```

A project can also keep its own copy of `SlideMage_citation_default.tex`; a copy in the project wins over the one
that comes with SlideMage.

## Other formats

The formats on [the citation formats page](../index.md) are installed from SlideMage (**Settings → Plugins →
Citation formats**) and chosen the same way, by their key.

---

Built into SlideMage · License LPPL-1.3c-or-later · [Source](https://github.com/SlideMage/SlideMage/blob/develop/latex/SlideMage_citation_default.tex)

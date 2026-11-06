# Citation formats

A citation format changes how references look: the biblatex options and the bibliography drivers behind
`\parencite`, `\textcite`, `\fullcite` and the reference list. It is a TeX file and no program. SlideMage ships
one format, the house format `default`; the ones below are installed from SlideMage or from a file.

## Available citation formats

<!-- catalogue:cards:start -->
!!! note "No citation formats listed yet"
    The first ones are in preparation.
<!-- catalogue:cards:end -->

## Using one

Install it in SlideMage (**Settings → Plugins → Citation formats**, from the catalogue, from GitHub or from a file), then
choose it by its key in a template (between `\input{SlideMage_setup}` and `\input{SlideMage_base}`) or in a deck
(before `\SMUseBibliography`):

```latex
\renewcommand{\SMCitationFormat}{apa}
```

A project's own copy of `SlideMage_citation_<key>.tex` wins over the installed one, which lets a project freeze a
version.

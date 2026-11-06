# Citation formats

A citation format changes how references look; it contains a TeX file and no program. SlideMage ships its
own house format; install another one to match a journal's or a publisher's style.

## Installing a citation format

- **In SlideMage:** under **Settings → Plugins → Citation formats**.
- **By hand:** download a citation format's `.smcite` file, then choose **Settings → Plugins → Citation
  formats → Install from file…**.

## Using one

In a template, before `\input{SlideMage_base}`:

```latex
\renewcommand{\SMCitationFormat}{<key>}
```

Or in a single deck, before `\SMUseBibliography`:

```latex
\renewcommand{\SMCitationFormat}{<key>}
```

## Available citation formats

<!-- catalogue:cards:start -->
!!! note "No citation formats listed yet"
    The first ones are in preparation.
<!-- catalogue:cards:end -->

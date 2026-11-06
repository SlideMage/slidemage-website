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

- **APA 7**: author-year citations and a reference list after the 7th edition
  ([source and README](https://github.com/SlideMage/slidemage-citation-apa)), key `apa`.
- **Chicago author-date**: after the Chicago Manual of Style, 17th edition
  ([source and README](https://github.com/SlideMage/slidemage-citation-chicago)), key `chicago`.
- **Harvard**: in the form of *Cite Them Right*
  ([source and README](https://github.com/SlideMage/slidemage-citation-harvard)), key `harvard`.

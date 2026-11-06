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
<div class="grid cards" markdown>

-   **[SlideMage house format](default/index.md)** · *Built in*

    Comes with SlideMage, nothing to install. The default: used by every deck unless a template or deck chooses
    another format.

    [![](default/preview.png){ loading=lazy }](default/index.md)

    Built in: comes with SlideMage, nothing to install

-   **[APA 7](apa/index.md)**

    Author-year citations and a reference list after APA 7 (7th edition), through biblatex-apa.

    [![](apa/preview.png){ loading=lazy }](apa/index.md)

    Version 1.0.0 · SlideMage &gt;=0.13.0 · by Stefan Palan

-   **[Chicago author-date](chicago/index.md)**

    Author-date citations and a reference list after the Chicago Manual of Style, 17th ed., through biblatex-chicago.

    [![](chicago/preview.png){ loading=lazy }](chicago/index.md)

    Version 1.0.0 · SlideMage &gt;=0.13.0 · by Stefan Palan

-   **[Harvard](harvard/index.md)**

    Harvard author-date citations and reference list in the form of Cite Them Right, on biblatex's authoryear style.

    [![](harvard/preview.png){ loading=lazy }](harvard/index.md)

    Version 1.0.0 · SlideMage &gt;=0.13.0 · by Stefan Palan

</div>
<!-- catalogue:cards:end -->

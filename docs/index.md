# SlideMage

**Slides for research and teaching, written in LaTeX, managed by a desktop app.**

SlideMage has two parts:

- **A LaTeX/beamer framework.** Every slide is its own file with a permanent ID, so one slide can be used in
  many decks and edited in one place. Templates set an institution's colors, logo and fonts.
- **The SlideMage app.** It's a desktop workspace for your decks. It compiles them, shows a preview of each
  slide, and keeps track of slide IDs, versions, image descriptions and transcripts.

## What it does

- **Reuse slides across decks.** Decks list slide IDs. When you change a slide, every deck that uses it
  follows, or keeps an older version if you pin one.
- **One deck, several versions.** Instructor, during-course and after-course versions come from the same
  source.
- **English and German** versions of a slide sit side by side.
- **Accessibility built in.** Image descriptions and accessible transcripts are part of the workflow, not an
  afterthought.
- **AI assistance, your choice of where.** Run a local model through Ollama, so nothing leaves your
  computer, or use Claude in the cloud. Both come as [plugins](plugins/index.md).

## Get started

See [Download](download.md). SlideMage needs a LaTeX installation with LuaLaTeX and biber.

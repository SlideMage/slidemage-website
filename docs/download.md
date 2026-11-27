# Download

SlideMage is free software for Windows and Linux. These links always give you the
[latest release](https://github.com/SlideMage/SlideMage/releases/latest):

| | Windows | Linux |
|---|---|---|
| **Folder build** (starts faster) | [SlideMage-windows-folder.zip](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-windows-folder.zip) | [SlideMage-linux-folder.zip](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-linux-folder.zip) |
| **Single file** | [SlideMage-windows.zip](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-windows.zip) | [SlideMage-linux.zip](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-linux.zip) |

Unzip the download and start `SlideMage`. You don't need Python. The app checks for new releases and can
update itself.

## What you'll need

- A LaTeX distribution with **LuaLaTeX**, **biber** and **latexmk**, for example TeX Live or MiKTeX. With
  MiKTeX, latexmk also needs Perl.
- Optional: [Ollama](https://ollama.com) for local AI models, or Claude Code or an Anthropic API key for
  Claude. Both are added through [plugins](plugins/index.md).

On Linux, a bare system may lack libraries the app's built-in browser needs, such as `libnss3`,
`libxcomposite1`, `libxdamage1`, `libxrandr2`, `libxtst6` and an ALSA library. Install them with your package
manager.

## SlideMage Presenter

A small program that presents a PDF with a presenter view, without a SlideMage project. It also runs on
Macs with Apple silicon:
[Windows](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMagePresenter-windows.zip),
[Linux](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMagePresenter-linux.zip),
[macOS](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMagePresenter-macos.zip).
The macOS app is not signed: the first time, open it with a right-click, then **Open**.

## Source code

The source is on [GitHub](https://github.com/SlideMage/SlideMage).

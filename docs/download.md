# Download

SlideMage is free software for Windows and Linux. These links always give you the
[latest release](https://github.com/SlideMage/SlideMage/releases/latest).

## Install

The installers set up SlideMage for you, together with what it needs to compile slides: a LaTeX distribution
with LuaLaTeX, biber and latexmk, and the LaTeX packages SlideMage uses. They show what they will install and ask
first, keep a LaTeX installation you already have, and finish by compiling a test deck. They never change your
projects or settings, and you can run them again to repair or update SlideMage.

**Windows:** [Download SlideMage-Setup.exe](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-Setup.exe)
and run it. You don't need administrator rights. Without LaTeX it installs MiKTeX; without Perl (which latexmk
needs) it installs a portable Strawberry Perl. To remove SlideMage, use **Settings → Apps → Installed apps**.

**Linux** (Ubuntu 24.04, Debian 13, Fedora 40 or newer, on x86_64): open a terminal and run

```bash
curl -fsSL https://github.com/SlideMage/SlideMage/releases/latest/download/install-slidemage.sh | bash
```

Or [download install-slidemage.sh](https://github.com/SlideMage/SlideMage/releases/latest/download/install-slidemage.sh),
read it, and run `bash install-slidemage.sh`. It installs SlideMage to `~/.local/share/SlideMage`, adds the
`slidemage` command and a menu entry, and installs the missing system and LaTeX packages with `sudo`. It checks
the release's signature before installing it. `bash install-slidemage.sh --uninstall` removes SlideMage again.

The app checks for new releases and can update itself.

## Download without installing

For macOS, or to set things up yourself: unzip the download and start `SlideMage`. You don't need Python.

| | Windows | Linux |
|---|---|---|
| **Folder build** (starts faster) | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-windows-folder.zip) | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-linux-folder.zip) |
| **Single file** | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-windows.zip) | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMage-linux.zip) |

You'll need:

- A LaTeX distribution with **LuaLaTeX**, **biber** and **latexmk**, for example TeX Live or MiKTeX. With
  MiKTeX, latexmk also needs Perl.
- On Linux, the libraries the app's built-in browser needs, such as `libnss3`, `libxcomposite1`, `libxdamage1`,
  `libxrandr2`, `libxtst6` and an ALSA library. Install them with your package manager.

Optional for both: [Ollama](https://ollama.com) for local AI models, or Claude Code or an Anthropic API key for
Claude. Both are added through [plugins](plugins/index.md).

## SlideMage Presenter

A small program that presents a PDF with a presenter view, without a SlideMage project. It needs no LaTeX.

| | Windows | Linux | macOS (Apple silicon) |
|---|---|---|---|
| **SlideMage Presenter** | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMagePresenter-windows.zip) | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMagePresenter-linux.zip) | [Download](https://github.com/SlideMage/SlideMage/releases/latest/download/SlideMagePresenter-macos.zip) |

The macOS app is not signed: the first time, open it with a right-click, then **Open**.

## Source code

The source is on [GitHub](https://github.com/SlideMage/SlideMage).

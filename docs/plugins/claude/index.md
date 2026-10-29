# Claude

![](icon.svg){ width="64" } Claude Code and the Anthropic API as SlideMage's cloud AI.

!!! info "What leaves your computer"
    This plugin contacts:

    - Anthropic: api.anthropic.com and Claude Code's own connections

## Requirements

- Claude Code installed and signed in, or an Anthropic API key

Works with SlideMage &gt;=9.1.

## Installing

In SlideMage: **Settings → Plugins** or **Help → Plugins…**.

By hand: download [Claude 1.0.1](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.1/claude-1.0.1.smplugin) (58 kB), then choose **Settings → Plugins → Install from file…**.

## About this plugin

Claude as SlideMage's cloud AI, in two ways. Both do the same jobs (the chat, drafting and translating slides, describing images); you choose
which one SlideMage uses, and can switch at any time.

- **Claude Code.** SlideMage opens Claude Code, Anthropic's coding assistant, in a terminal beside the editor and connects it to the open deck.
  Claude Code reads and edits your slides with SlideMage's own tools, and stays inside what you are looking at: the **Slide / Deck** switch above
  the terminal says how far a request may reach. Parts of a slide that are protected (SlideMage's protected regions) are refused, whatever
  Claude Code tries. Tasks that run on their own, such as describing images, use Claude Code too.
- **The Anthropic API.** SlideMage talks to Anthropic directly with your API key, with no Claude Code installed. The chat is SlideMage's own, with
  the same tools; it needs nothing but the Python standard library.

**What leaves your computer.** With either way, the text of the slides you work on, the files and images your requests refer to, and
what you type go to Anthropic (`api.anthropic.com`). Claude Code makes its own further connections, as Anthropic describes for it; SlideMage does not
control them. The plugin sends nothing anywhere else. Your API key is kept in the system's keychain or in a file only you can read, never in a deck.

**What you need.** Either Claude Code, installed and signed in (Anthropic account with a subscription or API credit), or an Anthropic API key.
SlideMage 9.1 or later.

## Versions

| Version | SlideMage | Released | Download |
|---|---|---|---|
| 1.0.1 | &gt;=9.1 | 2026-10-29 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.1/claude-1.0.1.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.0.1) |
| 1.0.0 | &gt;=9.1 | 2026-10-29 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.0/claude-1.0.0.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.0.0) |

## Changelog

### v1.0.1

*2026-10-29 · website icon*

The plugin has its own icon on the SlideMage website and in the plugin list, a cloud with an AI sparkle; the plugin itself is unchanged.

### v1.0.0

*2026-10-29 · first release*

Claude Code and the Anthropic API as SlideMage's cloud AI, as a plugin; they were part of SlideMage up to v9.0.

---

Maintained by Jürgen Fleiß · License GPL-3.0-or-later · [Source](https://github.com/SlideMage/slidemage-plugin-claude)

# Claude

![](icon.svg){ width="64" } Claude Code and the Anthropic API as SlideMage's cloud AI.

!!! info "What leaves your computer"
    This plugin contacts:

    - Anthropic: api.anthropic.com and Claude Code's own connections

## Requirements

- Claude Code installed and signed in, or an Anthropic API key

Works with SlideMage &gt;=0.13.31.

## Installing

In SlideMage: **Settings → Plugins** or **Help → Plugins…**.

By hand: download [Claude 1.2.1](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.2.1/claude-1.2.1.smplugin) (61 kB), then choose **Settings → Plugins → Install from file…**.

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
| 1.2.1 | &gt;=0.13.31 | 2026-11-07 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.2.1/claude-1.2.1.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.2.1) |
| 1.2.0 | &gt;=0.13.31 | 2026-11-03 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.2.0/claude-1.2.0.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.2.0) |
| 1.0.3 | &gt;=9.1 | 2026-10-30 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.3/claude-1.0.3.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.0.3) |
| 1.0.2 | &gt;=9.1 | 2026-10-30 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.2/claude-1.0.2.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.0.2) |
| 1.0.1 | &gt;=9.1 | 2026-10-29 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.1/claude-1.0.1.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.0.1) |
| 1.0.0 | &gt;=9.1 | 2026-10-29 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-claude/releases/download/v1.0.0/claude-1.0.0.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-claude/releases/tag/v1.0.0) |

## Changelog

### v1.2.1

*2026-11-06 · protected parts as SlideMage defines them*

The hook and Claude Code's instructions name the protected parts of a slide as the running SlideMage applies them. From SlideMage v0.14.25 those are the '%%' lines at the top of a slide and its \setSlideVersion line, and the ordinary '%' notes at the top (sources, the user's instructions) are editable; an older SlideMage protects the whole comment block there. The plugin reads which rule applies from plugin_api.protected_spans. Overlay blocks (\vbox to 0pt&#123;...&#125;) are no longer named as protected: SlideMage stopped protecting them in v9.4.0, but the message and the instructions still said so, and Claude Code avoided editing them. The hook no longer refuses an edit because the protected lines stopped being the first thing in the file, so deleting a note above them is allowed.

### v1.2.0

*2026-11-02 · any language of the project, with SlideMage v0.13.31*

Claude Code translates image descriptions into the language SlideMage asks for, not only German: ClaudeTranslationBackend has a target_lang (German by default), the prompt is the one configured for English to that language, the answer schema has short, long and takeaway, and the result says its language. Requires SlideMage v0.13.31, whose image descriptions are per language.

### v1.1.0

*2026-10-30 · isolated chat requests*

Claude Code can answer one self-contained ai.chat request on the chosen model and effort, with tools, inherited MCP servers and settings disabled. Replies accept free text or JSON without task validation, report CLI truncation signals, and abort ends the process. The assistant conversation stays in the terminal.

### v1.0.3

*2026-10-30 · SlideMage names*

The hook finds the project with every SlideMage version: Claude Code gets the project folder as SLIDEMAGE_PROJECT, which SlideMage reads from v10 on, and as SLIDEMASTER_PROJECT for the versions before. The tests name the project variable through SlideMage and the bibliography SlideMage.bib.

### v1.0.2

*2026-10-30 · hook on Windows*

Claude Code no longer reports a failed UserPromptSubmit hook on Windows: the hook command now uses forward slashes in paths and double quotes, so Git Bash, which Claude Code runs it through, finds SlideMage.exe.

### v1.0.1

*2026-10-29 · website icon*

The plugin has its own icon on the SlideMage website and in the plugin list, a cloud with an AI sparkle; the plugin itself is unchanged.

### v1.0.0

*2026-10-29 · first release*

Claude Code and the Anthropic API as SlideMage's cloud AI, as a plugin; they were part of SlideMage up to v9.0.

---

Maintained by Jürgen Fleiß · License GPL-3.0-or-later · [Source](https://github.com/SlideMage/slidemage-plugin-claude)

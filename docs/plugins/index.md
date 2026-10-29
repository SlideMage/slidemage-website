# Plugins

Plugins add features to SlideMage. SlideMage works without any of them; install the ones you need.

## Available plugins

<!-- catalogue:cards:start -->
<div class="grid cards" markdown>

-   ![](claude/icon.svg){ width="40" } **[Claude](claude/index.md)** · *Recommended*

    Claude Code and the Anthropic API as SlideMage's cloud AI.

    **Needs:** Claude Code installed and signed in, or an Anthropic API key  
    **Contacts:** Anthropic: api.anthropic.com and Claude Code's own connections

    Version 1.0.1 · SlideMage &gt;=9.1 · by Jürgen Fleiß

-   ![](ollama/icon.svg){ width="40" } **[Ollama](ollama/index.md)** · *Recommended*

    Local AI models through Ollama: nothing leaves your computer.

    **Needs:** Ollama installed  
    **Contacts:** The Ollama server you set (by default on this computer)

    Version 1.0.1 · SlideMage &gt;=9.1 · by Stefan Palan

-   ![](campusonline/icon.svg){ width="40" } **[CampusOnline](campusonline/index.md)**

    Course links, admin slides and session-aware rendering for CAMPUSonline courses.

    **Needs:** A CAMPUSonline course page  
    **Contacts:** The CAMPUSonline server of the linked course

    Version 1.0.0 · SlideMage &gt;=9.0 · by Jürgen Fleiß

</div>
<!-- catalogue:cards:end -->

## Local or cloud AI?

Both AI plugins can be installed at the same time. The **Local | Cloud** switch in SlideMage's assistant
picks which one is used.

| | Ollama | Claude |
|---|---|---|
| Runs | on your computer | in the cloud |
| You need | Ollama installed and a capable computer | Claude Code, or an Anthropic API key |
| Your slides | never leave your computer | are sent to Anthropic |

## Installing a plugin

- **In SlideMage:** on first start, or later under **Settings → Plugins** or **Help → Plugins…**.
- **By hand:** download a plugin's `.smplugin` file, then choose **Settings → Plugins → Install from file…**.

## Writing a plugin

Anyone can write a plugin. Plugins listed here have been reviewed; [Submit a plugin](submit.md)
describes what a plugin repository needs and how the review works.

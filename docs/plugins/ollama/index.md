# Ollama

![](icon.svg){ width="64" } Local AI models through Ollama: nothing leaves your computer.

!!! info "What leaves your computer"
    This plugin contacts:

    - The Ollama server you set (by default on this computer)

## Requirements

- Ollama installed

Works with SlideMage &gt;=9.1.

## Installing

In SlideMage: **Settings → Plugins** or **Help → Plugins…**.

By hand: download [Ollama 1.0.0](https://github.com/SlideMage/slidemage-plugin-ollama/releases/download/v1.0.0/ollama-1.0.0.smplugin) (31 kB), then choose **Settings → Plugins → Install from file…**.

## About this plugin

Runs SlideMage's AI features on a model you have installed through [Ollama](https://ollama.com): drafting slides,
translating, describing images, and the agent chat. The Ollama tab of the Settings sheet shows the server's
address and the models installed there, and updates or deletes them.

- **Local models.** The features use the Ollama server you set: by default `http://localhost:11434` on this
  computer, or the `OLLAMA_HOST` environment variable.
- **Model management.** Update pulls the latest weights of an installed model (a custom model you built with
  `ollama create` is relinked to its refreshed base). Delete removes the model's files from Ollama's store.
  Administration shares the Ollama task reservation with SlideMage's AI work.

**Privacy.** When the server is on this computer, nothing leaves the computer: the prompts, the slides and the
answers stay between SlideMage and Ollama. The plugin contacts only the server address you set, and only for the
requests of the features above and the model list. If you point it at another machine, that machine gets the same
requests. For remote servers the plugin honours `HTTP_PROXY` or `HTTPS_PROXY` and `NO_PROXY` (including
lowercase forms and `ALL_PROXY`); proxy URLs must use `http://`. HTTPS uses a CONNECT tunnel. Loopback addresses
and `localhost` always connect directly. An HTTP proxy can see requests sent to a remote HTTP server.

**Requirements.** Ollama installed and running (ollama.com), and at least one model pulled, for example
`ollama pull qwen3`. The agent chat needs a model that can call tools.

## Versions

| Version | SlideMage | Released | Download |
|---|---|---|---|
| 1.0.0 | &gt;=9.1 | 2026-10-29 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-ollama/releases/download/v1.0.0/ollama-1.0.0.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-ollama/releases/tag/v1.0.0) |

## Changelog

### v1.0.0

*2026-10-29 · first release*

Local AI models through Ollama, as a plugin, built on SlideMage's plugin API 1: the Ollama provider for the chat, drafting and translation, and the Ollama tab of the Settings sheet (the server's address; update and delete of installed models).

---

Maintained by Stefan Palan · License GPL-3.0-or-later · [Source](https://github.com/SlideMage/slidemage-plugin-ollama)

# OpenAI-compatible

![](icon.svg){ width="64" } OpenAI, Mistral, OpenRouter, LM Studio or any other OpenAI-compatible server: your key, your model.

!!! info "What leaves your computer"
    This plugin contacts:

    - The OpenAI-compatible server you choose

## Requirements

- An API key for your chosen server, unless it runs locally without one

Works with SlideMage &gt;=9.1.

## Installing

In SlideMage: **Settings → Plugins** or **Help → Plugins…**.

By hand: download [OpenAI-compatible 0.9.0](https://github.com/SlideMage/slidemage-plugin-openai-compatible/releases/download/v0.9.0/openai-compatible-0.9.0.smplugin) (25 kB), then choose **Settings → Plugins → Install from file…**.

## About this plugin

Use OpenAI, Mistral, OpenRouter, LM Studio or any other OpenAI-compatible server as SlideMage's AI for chat,
image descriptions, translation and fixes.

1. Open **Settings → AI → OpenAI-compatible** and choose your **Server**:

   | Server | Setup |
   | --- | --- |
   | OpenAI | Choose OpenAI and get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). |
   | Mistral | Choose Mistral and get a key at [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys). |
   | OpenRouter | Choose OpenRouter and get a key at [openrouter.ai/keys](https://openrouter.ai/keys). |
   | LM Studio | Choose Other and enter `http://localhost:1234/v1` as the Base URL; no key is needed unless your server requires one. |
   | Another server | Choose Other and enter its OpenAI-compatible Base URL and key, if required. |

2. Paste the server's **API key** and click **Save key**. Each server host has its own stored key; switching
   servers restores that server's key. An empty save clears only the current server's key.
3. Click **Check connection**, then choose a model in **AI setup** (the ▾ of the AI switch).
   OpenRouter defaults to `openrouter/auto`. Add models missing from the list under **Extra model IDs**.

Your slides and prompts go to the server you choose, and to any model provider it routes them to.

## Versions

| Version | SlideMage | Released | Download |
|---|---|---|---|
| 0.9.0 | &gt;=9.1 | 2026-11-12 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-openai-compatible/releases/download/v0.9.0/openai-compatible-0.9.0.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-openai-compatible/releases/tag/v0.9.0) |

## Changelog

### v0.9.0

*2026-11-12 · first release*

An AI route for OpenAI-compatible /chat/completions servers.

NEW: OpenAI-compatible servers in SlideMage, with your own key and model.
- Choose OpenAI, Mistral or OpenRouter under Settings → AI → OpenAI-compatible for chat, image descriptions, translation and fixes.
- Connect LM Studio, vLLM, Ollama's /v1 or another OpenAI-compatible server by choosing Other and setting its base URL.
- Keep a separate API key for each server host; switching servers restores its own key.
- Add a model the server does not list under Extra model IDs.
- Check connection shows whether the server and key work, and how many models it offers.
- Mistral's reasoning models answer with their text only; their thinking is left out.

---

Maintained by Jürgen Fleiß · License GPL-3.0-or-later · [Source](https://github.com/SlideMage/slidemage-plugin-openai-compatible)

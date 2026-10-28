# Submit a plugin

Anyone can write a SlideMage plugin. To have it listed here and in SlideMage's own list of plugins, it
needs a short review. This page describes what a plugin repository must look like and how the review works.

!!! note "Plugin support is coming"
    SlideMage doesn't load plugins yet. The conventions on this page are settled; the plugin API they build
    on (`slidemage.plugin_api`) will be documented with the first SlideMage release that supports plugins.

## The repository

Each plugin has its own public GitHub repository, named `slidemage-plugin-<id>` by convention, on its
author's account. The easiest start is the
[plugin template](https://github.com/SlideMage/slidemage-plugin-template): it has the layout below and a
`build.py` that builds the release asset reproducibly.

```
slidemage-plugin-<id>/
  plugin.toml
  <package>/__init__.py
  LICENSE
  README.md
  CHANGELOG.md
  website/icon.svg             optional
  website/screenshots/*.png    optional
```

### `plugin.toml`

| Field | Rule | Example |
|---|---|---|
| `id` | lowercase letters, digits and hyphens, 2–32 characters, starting with a letter; never changes | `"my-plugin"` |
| `name` | 1–40 characters | `"My Plugin"` |
| `version` | `MAJOR.MINOR.PATCH` | `"1.2.0"` |
| `api_version` | the SlideMage plugin API it is written for, an integer from 1 | `1` |
| `requires_slidemage` | a version range: comparisons (`>=`, `<`, `==`) separated by commas | `">=9.0, <10"` |
| `summary` | one sentence, at most 120 characters | `"Adds a slide counter to every deck."` |
| `author` | free text | `"Ada Example"` |
| `homepage` | an https URL, usually the repository | `"https://github.com/ada/slidemage-plugin-my-plugin"` |
| `license` | an SPDX expression | `"GPL-3.0-or-later"` |
| `needs` | short lines: what the user must have; `[]` if nothing | `["A CAMPUSonline course page"]` |
| `network` | short lines: everything the plugin contacts; `[]` if nothing | `["The Ollama server on this computer"]` |

`summary`, `needs` and `network` are shown in SlideMage before a user installs the plugin, so keep them
accurate and short (at most 120 characters per line).

A few ids are taken: `submit` by this page, and `settings`, `secrets`, `pending`, `staging`, `old`, `state`,
`catalogue`, `last-update-check`, `offer-seen` and `migrations-seen` by SlideMage itself.

## Releases

- **Tag** `v<version>`, the same version as in `plugin.toml`.
- **One asset** named `<id>-<version>.smplugin`: a zip file with `plugin.toml` at its root, the plugin's
  package and `LICENSE`. Optionally a second asset `<id>-<version>.smplugin.sha256` in `sha256sum` format
  (`<hash>  <file name>`); if it is there, it is checked. No other assets.
- **Pure Python.** Compiled files (`.pyc`, `.so`, `.pyd`, `.dll`, …) in the asset refuse the release.
- **Drafts and pre-releases** are never listed.
- **A published version never changes.** Never replace an asset; a fix is a new version. The catalogue
  records the SHA-256 of every asset it lists; an asset that changes afterwards is taken out of the
  catalogue.

A release that breaks one of these rules is left out of the catalogue; the plugin's other versions stay
listed.

## What the website shows

Each listed plugin gets a page at `/plugins/<id>/` and a card on [Plugins](index.md). They're built from
the repository at the newest listed release:

| Path | Used for | Required |
|---|---|---|
| `README.md` | the description on the plugin's page, up to a `## Development`, `## Building` or `## Contributing` heading | yes |
| `CHANGELOG.md` | the version history on the plugin's page: one entry per version, oldest first, each starting `v1.2.0 (2026-11-02, reason): ` | yes |
| `website/icon.svg` or `website/icon.png` | the icon; an SVG without scripts, or a square PNG of at least 128 px | no |
| `website/screenshots/*.png` | the gallery, in file name order; at most 6, at most 1 MB each | no |

Plugin texts are shown as plain Markdown: HTML is shown as text, images in the README appear as their alt
text (put screenshots in `website/screenshots/`), and relative links point to your repository.

## The review

A reviewer checks that:

- the repository and the release follow the conventions above;
- the license is compatible with the GPL (SlideMage is GPL-3.0-or-later, and plugins run in its process);
- the code imports only `slidemage.plugin_api`, the Python standard library, PySide6 and its own modules,
  and is pure Python;
- `network` names everything the code contacts, and `needs` is complete;
- the README says what the plugin does, without claims the code doesn't back;
- the maintainer is reachable: issues are open on the repository.

## How to submit

Either way, the review happens in a pull request to the
[website repository](https://github.com/SlideMage/slidemage-website); merging it is the approval.

- **A pull request:** add an entry to `registry/plugins.toml` and fill in the checklist the pull request
  shows. Its checks build the catalogue with your entry, so a problem shows up before the review.

    ```toml
    [[plugin]]
    id = "my-plugin"
    repository = "ada/slidemage-plugin-my-plugin"
    maintainer = "Ada Example"
    recommended = false
    releases = ["1.0.0"]
    yanked = []
    ```

- **The form:** [submit a plugin](https://github.com/SlideMage/slidemage-website/issues/new?template=submit-plugin.yml)
  as an issue, and the pull request is made for you.

A plugin starts with a list of approved versions. Each new version is a one-line pull request that adds it
to `releases`, approved after a look at what changed. A maintainer with a record of careful releases can
later have every new release listed automatically.

Once approved, a version appears in the catalogue within the hour. If a listed version turns out to have a
serious bug or a security problem, it is taken out of the catalogue ("yanked"); report such problems as an
[issue](https://github.com/SlideMage/slidemage-website/issues).

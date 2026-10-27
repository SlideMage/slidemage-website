<!--
Adding or changing a plugin in registry/plugins.toml? Fill in the checklist below; the conventions are on
https://stpalan.github.io/slidemage-website/plugins/submit/.
Any other change: delete everything below and say what the change does and why.
-->

## Plugin

- Id:
- Repository:
- Versions to approve:

## Review

Ticked by the reviewer; merging is the approval. CI builds the catalogue against this registry, so a
repository that breaks a convention fails here before it is listed.

**Repository and release**
- [ ] The repository and the release follow the conventions: tag `v<version>`, one asset
      `<id>-<version>.smplugin` (and optionally its `.sha256`), `plugin.toml` at the asset's root,
      `README.md` and `CHANGELOG.md` at the tag.
- [ ] The license is GPL-compatible (SlideMage is GPL-3.0-or-later and plugins run in its process), and
      `LICENSE` is in the asset.

**Code**
- [ ] The code imports only `slidemage.plugin_api`, the Python standard library, PySide6 and its own modules.
- [ ] It is pure Python: no compiled files in the `.smplugin`.
- [ ] `network` names everything the code contacts (an empty list only if it contacts nothing).
- [ ] `needs` lists everything the user must have.
- [ ] For a new version of a listed plugin: the diff since the last approved version was read.

**Description and maintainer**
- [ ] The README says what the plugin does, without claims the code doesn't back.
- [ ] The maintainer is reachable: issues are open on the repository.

**Registry entry**
- [ ] `recommended = false` (recommending is the website's decision).
- [ ] Third-party plugin: `releases` lists the approved versions; `"all"` only for first-party or trusted
      maintainers.
